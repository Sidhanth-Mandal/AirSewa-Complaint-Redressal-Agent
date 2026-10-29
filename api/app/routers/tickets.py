import hashlib
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import reference as R
from ..adapters import registry
from ..core import UPLOAD_DIR, bus, clock, get_db, iso
from ..deps import current_user, optional_user, require
from ..models import (Airport, Attachment, Notification, Organisation, SlaPolicy, Ticket, TicketEvent, User)
from ..modules import closure, sla
from ..modules import grievance as G

router = APIRouter(tags=["tickets"])

MAX_BYTES = 10 * 1024 * 1024
MAGIC = {".pdf": [b"%PDF"], ".png": [b"\x89PNG"], ".jpg": [b"\xff\xd8"], ".jpeg": [b"\xff\xd8"]}


# ------------------------------------------------------------------ meta
@router.get("/meta")
def meta(db: Session = Depends(get_db)):
    pols = db.query(SlaPolicy).filter(SlaPolicy.active == True).all()  # noqa: E712
    return {
        "categories": R.CATEGORIES, "subcategories": R.SUBCATEGORIES, "statuses": R.STATUSES,
        "airports": [{"id": a.id, "code": a.code, "name": a.name, "city": a.city, "state": a.state} for a in db.query(Airport).order_by(Airport.city)],
        "airlines": [{"id": o.id, "code": o.code, "name": o.name} for o in db.query(Organisation).filter(Organisation.type == "airline")],
        "orgs": [{"id": o.id, "code": o.code, "name": o.name, "type": o.type} for o in db.query(Organisation).order_by(Organisation.name)],
        "tat": {c: sla_tat(pols, c) for c in R.CATEGORIES}, "user_types": ["Passenger", "AAI", "Airline", "Airport Operator", "BCAS", "DGCA", "Airport Security Group (ASG)", "Flying Training Organization (FTO)", "Others"],
        "crisis_banner": G.cfg(db, "crisis_banner"), "allow_pre_breach_filing": G.cfg(db, "allow_pre_breach_filing"), "demo_mode": True,
        "clock": iso(clock.now()), "clock_offset_h": round(clock.offset.total_seconds() / 3600, 2),
    }


def sla_tat(pols, category):
    best, score = None, -1
    for p in pols:
        if p.severity or (p.category and p.category != category):
            continue
        s = 1 if p.category else 0
        if s > score:
            best, score = p, s
    crit = [p for p in pols if p.severity == 1]
    return {"standard_h": best.e1_hours if best else 24, "critical_h": crit[0].e1_hours if crit else 4}


@router.get("/booking/lookup")
def booking_lookup(airline: str, srn: str):
    """Mock airline booking lookup: auto-fetch flight number and PNR from airline + Service Request Number (FRS 3.2 #9)."""
    h = int(hashlib.md5((airline + srn).encode()).hexdigest(), 16)
    pnr = "".join("ABCDEFGHJKLMNPQRSTUVWXYZ23456789"[(h >> (5 * i)) % 32] for i in range(6))
    return {"flight_no": f"{airline.upper()[:2]}{100 + h % 899}", "pnr": pnr, "simulated": True}


# ------------------------------------------------------------------ create
class TicketIn(BaseModel):
    category: str
    description: str = Field(min_length=10, max_length=4000)
    contact_name: str | None = None
    contact_mobile: str | None = None
    contact_email: str | None = None
    airline_org_id: int | None = None
    airport_id: int | None = None
    flight_no: str | None = None
    pnr: str | None = None
    service_request_no: str | None = None
    event_at: datetime | None = None
    sr_logged_at: datetime | None = None
    lang: str | None = None
    consent: bool = False
    ticket_amount: float | None = None
    block_time_hours: float | None = None
    baggage_weight_kg: float | None = None
    source_channel: str = "portal"


@router.post("/tickets")
def create(b: TicketIn, u: User | None = Depends(optional_user), db: Session = Depends(get_db)):
    if not u or u.role not in ("passenger", "agent"):
        raise HTTPException(401, "Please login (or continue as guest with OTP) to file a grievance")
    f = b.model_dump()
    if u.role == "passenger":
        f["contact_name"] = f.get("contact_name") or u.name
        f["contact_mobile"] = f.get("contact_mobile") or u.mobile
        f["contact_email"] = f.get("contact_email") or u.email
    G.validate_form(f)
    f["extra"] = {k: f.pop(k) for k in ("ticket_amount", "block_time_hours", "baggage_weight_kg") if f.get(k) is not None}
    for k in ("ticket_amount", "block_time_hours", "baggage_weight_kg"):
        f.pop(k, None)
    t = G.create_ticket(db, f, user=u if u.role == "passenger" else None, actor_label=(f"AirSewa Agent {u.name} (on behalf of caller)" if u.role == "agent" else None))
    db.commit()
    pol = db.get(SlaPolicy, t.sla_policy_id)
    return {"ticket_no": t.ticket_no, "id": t.id, "severity": t.severity, "severity_reason": t.severity_reason, "category": t.category, "subcategory": t.subcategory,
            "assigned_org": t.assigned_org.name if t.assigned_org else None, "level": t.level, "status": t.status, "tat_hours": pol.e1_hours if pol else None}


def _ticket(db, ref) -> Ticket:
    q = db.query(Ticket)
    t = q.filter(Ticket.id == int(ref)).first() if str(ref).isdigit() else q.filter(Ticket.ticket_no == ref).first()
    if not t:
        raise HTTPException(404, "Ticket not found")
    return t


def _vis(u, t):
    if not G.can_view(u, t):
        raise HTTPException(403, "You do not have access to this ticket")


@router.post("/tickets/{ref}/attachments")
async def upload(ref: str, file: UploadFile = File(...), kind: str = Form("upload"), u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _ticket(db, ref)
    _vis(u, t)
    name = file.filename or "file"
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in MAGIC:
        raise HTTPException(422, "Only PDF, JPG and PNG files are allowed")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File exceeds the 10 MB limit")
    if not any(data.startswith(m) for m in MAGIC[ext]):
        raise HTTPException(422, "File content does not match its extension")
    stored = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / stored).write_bytes(data)
    a = Attachment(ticket_id=t.id, filename=name[:190], stored=stored, mime=file.content_type, size=len(data),
                   kind="evidence" if (kind == "evidence" and u.role != "passenger") else "upload", at=clock.now())
    db.add(a)
    G.add_event(db, t, G.actor_name(u), u.role, "attachment", f"{a.kind} file added: {a.filename} ({len(data) // 1024} KB)")
    db.commit()
    return {"id": a.id, "filename": a.filename, "size": a.size, "kind": a.kind}


@router.get("/tickets/{ref}/attachments/{aid}")
def download(ref: str, aid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _ticket(db, ref)
    _vis(u, t)
    a = db.get(Attachment, aid)
    if not a or a.ticket_id != t.id:
        raise HTTPException(404)
    return FileResponse(UPLOAD_DIR / a.stored, filename=a.filename)


# ------------------------------------------------------------------ list / detail
@router.get("/tickets")
def list_tickets(q: str | None = None, status: str | None = None, category: str | None = None, severity: int | None = None, queue: str | None = None,
                 breached: bool | None = None, channel: str | None = None, org: str | None = None, level: int | None = None, mine: bool = False,
                 sort: str = "newest", page: int = 1, limit: int = Query(25, le=200), u: User = Depends(current_user), db: Session = Depends(get_db)):
    qq = G.visible_query(db, u)
    if q:
        like = f"%{q}%"
        qq = qq.filter(or_(Ticket.ticket_no.ilike(like), Ticket.description.ilike(like), Ticket.pnr.ilike(like), Ticket.flight_no.ilike(like)))
    if status == "open":
        qq = qq.filter(Ticket.status.in_(R.OPEN_STATUSES))
    elif status:
        qq = qq.filter(Ticket.status == status)
    if category:
        qq = qq.filter(Ticket.category == category)
    if severity:
        qq = qq.filter(Ticket.severity == severity)
    if queue:
        qq = qq.filter(Ticket.queue == queue)
    if breached is not None:
        qq = qq.filter(Ticket.breached == breached)
    if channel:
        qq = qq.filter(Ticket.source_channel == channel)
    if org:
        qq = qq.join(Organisation, Organisation.id == Ticket.assigned_org_id).filter(Organisation.code == org)
    if level:
        qq = qq.filter(Ticket.level == level)
    if mine:
        qq = qq.filter(Ticket.assigned_user_id == u.id)
    total = qq.count()
    order = {"newest": Ticket.created_at.desc(), "oldest": Ticket.created_at.asc(), "severity": (Ticket.severity.asc(), Ticket.created_at.asc()),
             "due": Ticket.due_at.asc()}.get(sort, Ticket.created_at.desc())
    qq = qq.order_by(*order) if isinstance(order, tuple) else qq.order_by(order)
    items = qq.offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "items": [G.ticket_out(t, u) for t in items]}


def sla_info(db, t):
    p = db.get(SlaPolicy, t.sla_policy_id) if t.sla_policy_id else None
    if not p:
        return None
    ts = sla.time_state(t, p) if t.status in R.OPEN_STATUSES or t.status == "Provisionally Resolved" else None
    return {"policy": p.name, "e1_hours": p.e1_hours, "e2_hours": p.e2_hours, "e3_hours": p.e3_hours, "state": ts,
            "deadline": iso((t.sla_start or t.created_at) + timedelta(hours=p.e1_hours))}


@router.get("/tickets/{ref}")
def detail(ref: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _ticket(db, ref)
    _vis(u, t)
    # FRS 3.3 #14: status becomes In-Progress when the grievance is accessed by redressor staff
    if u.role in ("redressor", "nodal") and t.status in ("Assigned", "Reopened", "Escalated"):
        G.transition(db, t, "In-Progress", u, "Grievance opened by redressor staff", etype="accessed")
        if not t.first_response_at:
            t.first_response_at = clock.now()
        db.commit()
    atts = db.query(Attachment).filter(Attachment.ticket_id == t.id).all()
    nots = db.query(Notification).filter(Notification.ticket_id == t.id).order_by(Notification.at.desc()).limit(30).all()
    if u.role == "passenger":
        nots = [n for n in nots if n.user_id in (u.id, None) or n.channel in ("sms", "email")]
    children = db.query(Ticket).filter(Ticket.parent_id == t.id).all()
    out = G.ticket_out(t, u, detail=True)
    out.update({
        "events": G.events_out(db, t, u), "sla": sla_info(db, t), "children": [{"ticket_no": c.ticket_no, "status": c.status, "description": c.description[:80]} for c in children],
        "attachments": [{"id": a.id, "filename": a.filename, "size": a.size, "kind": a.kind} for a in atts],
        "notifications": [{"channel": n.channel, "to": n.to, "subject": n.subject, "body": n.body, "at": iso(n.at)} for n in nots],
        "can_reopen": t.status in ("Resolved", "Provisionally Resolved", "Closed") and t.reopen_count < (G.cfg(db, "max_reopens") or 2),
        "max_reopens": G.cfg(db, "max_reopens") or 2,
        "car_rule": (lambda r: {"code": r[0], "title": r[1]} if r else None)(closure.find_rule(db, t.subcategory)),
        "staff_in_org": ([{"id": s.id, "name": s.name, "level": s.level} for s in db.query(User).filter(User.org_id == t.assigned_org_id, User.role == "redressor", User.status == "active")]
                         if u.role in ("redressor", "nodal", "agent", "admin") else []),
    })
    if t.parent_id:
        p = db.get(Ticket, t.parent_id)
        out["parent_ticket_no"] = p.ticket_no if p else None
    return out


# ------------------------------------------------------------------ actions
class ActionIn(BaseModel):
    action: str
    note: str | None = None
    reason: str | None = None
    resolution_text: str | None = None
    amount: float | None = None
    txn_id: str | None = None
    reference: str | None = None
    remedy_complete: bool = True
    to_org_id: int | None = None
    org_id: int | None = None
    user_id: int | None = None
    severity: int | None = None
    category: str | None = None
    subcategory: str | None = None
    airport_id: int | None = None
    rating: int | None = None
    confirms: bool | None = None
    ok: bool | None = None
    decision: str | None = None
    parent_ref: str | None = None
    message: str | None = None


def _staff_write(u: User, t: Ticket):
    if u.role == "redressor":
        if u.access_type == "read":
            raise HTTPException(403, "Your account has read-only access")
        if t.level > u.level and t.assigned_user_id != u.id:
            raise HTTPException(403, "This ticket is escalated beyond your level")


@router.post("/tickets/{ref}/action")
def action(ref: str, b: ActionIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _ticket(db, ref)
    _vis(u, t)
    a = b.action
    now = clock.now()
    staff = u.role in ("redressor", "nodal")
    result = {}
    note = b.note or b.reason or b.message or ""
    if a == "comment":
        G.add_event(db, t, G.actor_name(u), u.role, "comment", note)
        if staff and not t.first_response_at:
            t.first_response_at = now
    elif staff and a == "start":
        _staff_write(u, t)
        G.transition(db, t, "In-Progress", u, note or "Work started")
        t.first_response_at = t.first_response_at or now
    elif staff and a == "hold":
        _staff_write(u, t)
        if not note:
            raise HTTPException(422, "Please state what information is needed from the passenger")
        t.hold_reason = note
        G.transition(db, t, "On Hold - Awaiting Passenger Inputs", u, note, etype="hold")
        t.first_response_at = t.first_response_at or now
    elif a in ("resume", "provide_info") and ((staff and a == "resume") or (u.role == "passenger" and a == "provide_info")):
        if t.status != "On Hold - Awaiting Passenger Inputs":
            raise HTTPException(409, "Ticket is not on hold")
        G.transition(db, t, "In-Progress", u, note or "Passenger inputs received" if a == "provide_info" else "Resumed")
    elif staff and a == "resolve":
        _staff_write(u, t)
        nfiles = db.query(Attachment).filter(Attachment.ticket_id == t.id, Attachment.kind == "evidence").count()
        result["compliance"] = closure.resolve(db, t, u, b.resolution_text or "", {"amount": b.amount, "txn_id": b.txn_id, "reference": b.reference}, b.remedy_complete, nfiles)
    elif staff and a == "divert":
        _staff_write(u, t)
        org = db.get(Organisation, b.to_org_id) if b.to_org_id else None
        if not org:
            raise HTTPException(422, "Select the organisation to divert to")
        old = t.assigned_org.name if t.assigned_org else "-"
        t.assigned_org_id, t.transfer_count = org.id, t.transfer_count + 1
        t.level = t.start_level or 1
        nu = G.assign_user(db, org.id, t.level)
        t.assigned_user_id = nu.id if nu else None
        t.team = org.name
        G.add_event(db, t, G.actor_name(u), u.role, "diverted", f"Diverted {old} -> {org.name}: {note}")
        t.status = "Assigned"
        G.on_status_changed(db, t, "In-Progress", "Assigned")
    elif staff and a == "add_redressor":
        _staff_write(u, t)
        if not b.org_id:
            raise HTTPException(422, "Select an organisation")
        t.extra_org_ids = list({*(t.extra_org_ids or []), b.org_id})
        o = db.get(Organisation, b.org_id)
        G.add_event(db, t, G.actor_name(u), u.role, "redressor_added", f"Additional redressor added: {o.name if o else b.org_id}. {note}")
    elif staff and a == "escalate":
        _staff_write(u, t)
        if t.level >= 4:
            raise HTTPException(409, "Already at Nodal level")
        t.level += 1
        t.escalation_count += 1
        nu = G.assign_user(db, t.assigned_org_id, t.level)
        t.assigned_user_id = nu.id if nu else None
        frm = t.status
        t.status = "Escalated"
        G.add_event(db, t, G.actor_name(u), u.role, "escalation", f"Manually escalated to {sla.LEVEL_NAME[t.level]}: {note}", frm, "Escalated")
        G.on_status_changed(db, t, frm, "Escalated")
    elif a == "severity" and (staff or u.role in ("agent", "admin")):
        sev = b.severity
        if sev not in (1, 2, 3, 4):
            raise HTTPException(422, "Severity must be 1-4")
        if not note:
            raise HTTPException(422, "A reason is required to change severity")
        if u.role == "redressor" and u.level < 2:
            raise HTTPException(403, "Only L2 and above can override severity")
        if sev == t.severity:
            raise HTTPException(409, "Severity unchanged")
        if sev < t.severity or u.role == "agent":  # upgrade (lower number = higher severity), or agent either way
            old = t.severity
            t.severity = sev
            t.severity_reason = f"S{sev}: overridden by {u.name} ({u.role}) from S{old}. {note}"
            G.add_event(db, t, G.actor_name(u), u.role, "severity_override", f"S{old} -> S{sev}. {note}")
        else:  # downgrade requested by staff: needs L3 / Nodal approval (FRS 3.3 #34)
            if u.role == "nodal" or (u.role == "redressor" and u.level == 3 and False):
                pass
            t.downgrade_request = {"to": sev, "by": u.name, "reason": note, "at": iso(now)}
            G.add_event(db, t, G.actor_name(u), u.role, "downgrade_requested", f"Downgrade S{t.severity} -> S{sev} requested; awaiting L3/Nodal approval. {note}")
            result["pending_approval"] = True
    elif a in ("approve_downgrade", "reject_downgrade") and (u.role == "nodal" or (u.role == "redressor" and u.level == 3)):
        dr = t.downgrade_request
        if not dr:
            raise HTTPException(409, "No downgrade request pending")
        if a == "approve_downgrade":
            old = t.severity
            t.severity = dr["to"]
            t.severity_reason = f"S{t.severity}: downgraded from S{old} (approved by {u.name}). Reason: {dr['reason']}"
            G.add_event(db, t, G.actor_name(u), u.role, "severity_override", f"Downgrade approved S{old} -> S{t.severity}")
        else:
            G.add_event(db, t, G.actor_name(u), u.role, "downgrade_rejected", note)
        t.downgrade_request = None
    elif a == "assign" and (u.role in ("nodal", "agent") or (u.role == "redressor" and u.level == 3)):
        nu = db.get(User, b.user_id) if b.user_id else None
        if not nu or nu.org_id != t.assigned_org_id:
            raise HTTPException(422, "Select a staff member of the assigned organisation")
        t.assigned_user_id, t.level = nu.id, max(nu.level or 1, 1) if nu.role == "redressor" else 4
        G.add_event(db, t, G.actor_name(u), u.role, "reassigned", f"Manually assigned to {nu.name} (L{nu.level})")
    # ---------------- passenger
    elif u.role == "passenger" and a == "feedback":
        if not b.rating or not 1 <= b.rating <= 5:
            raise HTTPException(422, "Rating 1-5 is required")
        result["outcome"] = closure.passenger_feedback(db, t, u, b.rating, bool(b.confirms), note)
    elif u.role == "passenger" and a == "reopen":
        if t.status not in ("Resolved", "Provisionally Resolved", "Closed"):
            raise HTTPException(409, "Only resolved/closed grievances can be reopened")
        if t.reopen_count >= (G.cfg(db, "max_reopens") or 2):
            raise HTTPException(409, f"A grievance can be reopened at most {G.cfg(db, 'max_reopens') or 2} times. Use 'Dispute' to refer it to the Case Closure Committee.")
        result["outcome"] = closure.reopen_or_dispute(db, t, u, note or "Passenger reopened")
    elif u.role == "passenger" and a == "dispute":
        if t.status not in ("Resolved", "Provisionally Resolved", "Closed"):
            raise HTTPException(409, "Only resolved grievances can be disputed")
        result["outcome"] = closure.dispute(db, t, u, note or "Passenger disputes the resolution")
    elif u.role == "passenger" and a == "escalate":
        if t.status not in R.OPEN_STATUSES:
            raise HTTPException(409, "Only open grievances can be escalated")
        if t.level >= 4:
            raise HTTPException(409, "Already escalated to the highest level")
        t.level += 1
        t.escalation_count += 1
        nu = G.assign_user(db, t.assigned_org_id, t.level)
        t.assigned_user_id = nu.id if nu else None
        frm = t.status
        t.status = "Escalated"
        G.add_event(db, t, G.actor_name(u), "passenger", "escalation", f"Passenger escalated to {sla.LEVEL_NAME[t.level]}: {note}", frm, "Escalated")
        G.on_status_changed(db, t, frm, "Escalated")
    # ---------------- agent
    elif u.role in ("agent", "admin") and a == "reclassify":
        if u.role != "agent":
            raise HTTPException(403, "Only AirSewa Agents can override classification")
        ch = []
        if b.category and b.category != t.category:
            if b.category not in R.CATEGORIES:
                raise HTTPException(422, "Invalid category")
            ch.append(f"category {t.category}->{b.category}")
            t.category = b.category
        if b.subcategory and b.subcategory != t.subcategory:
            ch.append(f"subcategory {t.subcategory}->{b.subcategory}")
            t.subcategory = b.subcategory
        if b.airport_id:
            t.airport_id = b.airport_id
        if b.to_org_id and b.to_org_id != t.assigned_org_id:
            o = db.get(Organisation, b.to_org_id)
            ch.append(f"assignee {t.assigned_org.name if t.assigned_org else '-'}->{o.name}")
            t.assigned_org_id, t.transfer_count = o.id, t.transfer_count + 1
            nu = G.assign_user(db, o.id, t.level)
            t.assigned_user_id = nu.id if nu else None
            t.team = o.name
        if b.severity and b.severity != t.severity:
            ch.append(f"severity S{t.severity}->S{b.severity}")
            t.severity = b.severity
            t.severity_reason = f"S{b.severity}: set by AirSewa Agent {u.name}. {note}"
        if not ch:
            raise HTTPException(409, "No change")
        G.add_event(db, t, G.actor_name(u), "agent", "override", "; ".join(ch) + f". {note}")
        db.query(Ticket).filter(Ticket.id == t.id).update({})
    elif u.role == "agent" and a == "merge":
        parent = _ticket(db, b.parent_ref or "")
        if parent.id == t.id:
            raise HTTPException(422, "Cannot merge a ticket into itself")
        t.parent_id = parent.id
        parent.related_count = (parent.related_count or 0) + 1
        G.add_event(db, parent, G.actor_name(u), "agent", "merged", f"{t.ticket_no} merged as child: {note}")
        G.add_event(db, t, G.actor_name(u), "agent", "merged", f"Merged into parent {parent.ticket_no}: {note}")
        t.resolution_text = f"Merged into {parent.ticket_no}"
        t.closed_at = now
        G.transition(db, t, "Closed", u, f"Merged into {parent.ticket_no}", etype="closed", force=True)
    elif u.role == "agent" and a == "reverify":
        closure.reverify(db, t, u, bool(b.ok), note)
    elif u.role in ("agent", "admin") and a == "committee":
        result["decision"] = closure.committee_decide(db, t, u, b.decision or "uphold", note)
    elif u.role == "agent" and a == "to_committee":
        closure.dispute(db, t, u, note or "Referred to Case Closure Committee by agent")
    else:
        raise HTTPException(403, f"Action '{a}' is not available for role '{u.role}'")
    t.updated_at = now
    G.audit(db, G.actor_name(u), f"ticket.{a}", t.ticket_no, note)
    db.commit()
    bus.publish("tickets", {"type": "action", "ticket_no": t.ticket_no, "action": a})
    return {"ok": True, "status": t.status, **result}


class BulkIn(BaseModel):
    ids: list[int]
    action: str  # severity | assign_org | escalate | note
    value: int | None = None
    note: str = ""


@router.post("/tickets/bulk")
def bulk(b: BulkIn, u: User = Depends(require("agent")), db: Session = Depends(get_db)):
    ts = db.query(Ticket).filter(Ticket.id.in_(b.ids[:500])).all()
    n = 0
    for t in ts:
        if b.action == "severity" and b.value in (1, 2, 3, 4):
            G.add_event(db, t, G.actor_name(u), "agent", "severity_override", f"[bulk] S{t.severity} -> S{b.value}. {b.note}")
            t.severity, t.severity_reason = b.value, f"S{b.value}: bulk override by {u.name}. {b.note}"
        elif b.action == "assign_org" and b.value:
            o = db.get(Organisation, b.value)
            if not o:
                continue
            t.assigned_org_id, t.transfer_count, t.team = o.id, t.transfer_count + 1, o.name
            nu = G.assign_user(db, o.id, t.level)
            t.assigned_user_id = nu.id if nu else None
            G.add_event(db, t, G.actor_name(u), "agent", "override", f"[bulk] assigned to {o.name}. {b.note}")
        elif b.action == "note":
            G.add_event(db, t, G.actor_name(u), "agent", "comment", f"[bulk] {b.note}")
        else:
            continue
        n += 1
    G.audit(db, u.name, "ticket.bulk", b.action, f"{n} tickets")
    db.commit()
    return {"updated": n}


@router.get("/track/{ticket_no}")
def public_track(ticket_no: str, mobile4: str | None = None, db: Session = Depends(get_db)):
    """Limited public status check: needs ticket ID + last 4 digits of the registered mobile (privacy)."""
    t = db.query(Ticket).filter(Ticket.ticket_no == ticket_no.upper()).first()
    if not t or not mobile4 or not (t.contact_mobile or "").endswith(mobile4):
        raise HTTPException(404, "No grievance found for these details")
    return {"ticket_no": t.ticket_no, "status": t.status, "category": t.category, "created_at": iso(t.created_at), "updated_at": iso(t.updated_at),
            "severity": t.severity, "assigned_org": t.assigned_org.name if t.assigned_org else None,
            "timeline": [{"at": iso(e.at), "to": e.to_status, "type": e.type} for e in db.query(TicketEvent).filter(TicketEvent.ticket_id == t.id, TicketEvent.to_status != None).order_by(TicketEvent.at)]}  # noqa: E711
