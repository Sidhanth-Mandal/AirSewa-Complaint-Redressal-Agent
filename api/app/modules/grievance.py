"""Grievance service layer: creation, status lifecycle (FRS 3.3), event log, notifications, serialization/masking."""
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func

from .. import reference as R
from ..adapters import registry
from ..core import bus, clock, iso, mask_email, mask_handle, mask_mobile, mask_name
from ..models import (AuditLog, Config, Organisation, SlaPolicy, Ticket, TicketEvent, User, Airport, SocialNotification)
from . import allocation

TRANSITIONS = {
    "Under Assessment": ["Assigned", "Escalated", "Closed"],
    "Assigned": ["In-Progress", "On Hold - Awaiting Passenger Inputs", "Escalated", "Provisionally Resolved", "Resolved", "Assigned"],
    "In-Progress": ["On Hold - Awaiting Passenger Inputs", "Provisionally Resolved", "Resolved", "Escalated", "Assigned"],
    "On Hold - Awaiting Passenger Inputs": ["In-Progress", "Escalated", "Resolved", "Provisionally Resolved", "Assigned"],
    "Provisionally Resolved": ["Resolved", "Closed", "Reopened", "In-Progress"],
    "Resolved": ["Closed", "Reopened"],
    "Reopened": ["Assigned", "In-Progress", "On Hold - Awaiting Passenger Inputs", "Escalated", "Resolved", "Provisionally Resolved"],
    "Escalated": ["In-Progress", "Assigned", "On Hold - Awaiting Passenger Inputs", "Resolved", "Provisionally Resolved", "Escalated"],
    "Closed": ["Reopened"],
}


# ------------------------------------------------------------------ config / audit helpers
def cfg(db, key):
    row = db.get(Config, key)
    return row.value if row is not None else R.CONFIG_DEFAULTS.get(key)


def set_cfg(db, key, value):
    row = db.get(Config, key)
    if row:
        row.value = value
    else:
        db.add(Config(key=key, value=value))


def audit(db, actor, action, entity="", detail=""):
    db.add(AuditLog(at=clock.now(), actor=str(actor), action=action, entity=entity, detail=str(detail)[:500]))


def add_event(db, t: Ticket, actor, role, etype, note="", from_status=None, to_status=None, data=None, at=None):
    db.add(TicketEvent(ticket_id=t.id, at=at or clock.now(), actor=actor, actor_role=role, type=etype, from_status=from_status,
                       to_status=to_status, note=note, data=data or {}))


def actor_name(user):
    return f"{user.name} ({user.org.code if user.org else user.role})" if user else "System"


def transition(db, t: Ticket, to: str, user=None, note="", etype="status", at=None, force=False):
    if t.status == to and to != "Escalated":
        return
    if not force and to not in TRANSITIONS.get(t.status, []):
        raise HTTPException(409, f"Invalid status change {t.status} -> {to}")
    frm = t.status
    t.status = to
    t.updated_at = at or clock.now()
    add_event(db, t, actor_name(user), user.role if user else "system", etype, note, frm, to, at=at)
    on_status_changed(db, t, frm, to)


def next_ticket_no(db, year: int) -> str:
    key = f"seq_{year}"
    row = db.get(Config, key)
    n = (row.value if row else 0) + 1
    if row:
        row.value = n
    else:
        db.add(Config(key=key, value=n))
    db.flush()
    return f"AS-{year}-{n:06d}"


def pick_policy(db, category, severity) -> SlaPolicy:
    pols = db.query(SlaPolicy).filter(SlaPolicy.active == True).all()  # noqa: E712
    best, score = None, -1
    for p in pols:
        if p.category and p.category != category:
            continue
        if p.severity and p.severity != severity:
            continue
        s = (2 if p.severity else 0) + (1 if p.category else 0)
        if s > score:
            best, score = p, s
    return best


def assign_user(db, org_id, level):
    """Least-loaded active staff of that org at exactly that level (workload based allocation)."""
    if not org_id:
        return None
    if level >= 4:
        return db.query(User).filter(User.org_id == org_id, User.role == "nodal", User.status == "active").first()
    cands = db.query(User).filter(User.org_id == org_id, User.role == "redressor", User.level == level, User.status == "active").all()
    if not cands:
        cands = db.query(User).filter(User.org_id == org_id, User.role == "redressor", User.level >= level, User.status == "active").all()
    if not cands:
        return db.query(User).filter(User.org_id == org_id, User.role == "nodal", User.status == "active").first()
    loads = dict(db.query(Ticket.assigned_user_id, func.count()).filter(
        Ticket.assigned_user_id.in_([c.id for c in cands]), Ticket.status.in_(R.OPEN_STATUSES)).group_by(Ticket.assigned_user_id).all())
    return min(cands, key=lambda c: loads.get(c.id, 0))


# ------------------------------------------------------------------ notifications
STATUS_MSG = {
    "Assigned": "Your grievance {no} has been assigned to {org}.",
    "On Hold - Awaiting Passenger Inputs": "Your grievance {no} is on hold: the officer needs more information from you. Please respond.",
    "Provisionally Resolved": "Your grievance {no} has been provisionally resolved. Please review and give feedback.",
    "Resolved": "Your grievance {no} has been resolved. Please confirm in feedback.",
    "Closed": "Your grievance {no} is closed. Thank you.",
    "Reopened": "Your grievance {no} has been reopened.",
    "Escalated": "Your grievance {no} has been escalated for priority attention.",
}


def notify_passenger(db, t: Ticket, subject, body):
    for ch, to in (("sms", t.contact_mobile), ("email", t.contact_email)):
        if to:
            registry.notifier.send(db, ch, to, subject, body, ticket_id=t.id, user_id=t.user_id)
    if t.user_id:
        registry.notifier.send(db, "inapp", "in-app", subject, body, ticket_id=t.id, user_id=t.user_id)


def on_status_changed(db, t, frm, to):
    msg = STATUS_MSG.get(to)
    if msg and t.source_channel != "seed":
        body = msg.format(no=t.ticket_no, org=t.assigned_org.name if t.assigned_org else "the concerned stakeholder")
        notify_passenger(db, t, f"AirSewa {t.ticket_no}: {to}", body)
        if t.social_post_id and to in ("Assigned", "Resolved", "Closed", "Escalated"):
            db.add(SocialNotification(handle=t.social_handle, kind="status", text=body, from_handle="@AirSewa_Official",
                                      post_id=t.social_post_id, ticket_no=t.ticket_no, at=clock.real_now()))
            bus.publish(f"social_notif:{(t.social_handle or '').lower()}", {"ticket_no": t.ticket_no, "text": body})
    bus.publish("tickets", {"type": "status", "ticket_no": t.ticket_no, "status": to, "severity": t.severity})


# ------------------------------------------------------------------ creation
CATEGORY_MANDATORY = {
    "flight": ["contact", "description", "event_at", "airline_org_id", "service_request_no", "pnr", "flight_no"],
    "airport": ["contact", "description", "event_at", "airport_id"],
    "ground": ["contact", "description", "event_at"],
    "govt": ["contact", "description", "event_at"],
    "other": ["contact", "description"],
}


def validate_form(f: dict):
    cat = f.get("category")
    if cat not in R.CATEGORIES:
        raise HTTPException(422, "Invalid category")
    missing = []
    for fld in CATEGORY_MANDATORY[cat]:
        if fld == "contact":
            if not (f.get("contact_mobile") or f.get("contact_email")):
                missing.append("contact_details")
        elif not f.get(fld):
            missing.append(fld)
    if missing:
        raise HTTPException(422, {"message": "Mandatory fields missing", "fields": missing})
    if not f.get("consent"):
        raise HTTPException(422, {"message": "Privacy consent is required", "fields": ["consent"]})
    if len(f.get("description", "").strip()) < 10:
        raise HTTPException(422, {"message": "Description is too short", "fields": ["description"]})


def create_ticket(db, f: dict, user=None, created_at=None, notify=True, actor_label=None) -> Ticket:
    """f: validated form-like dict. Applies translation, classification, routing, SLA and notifications."""
    now = created_at or clock.now()
    desc = f["description"].strip()
    lang = f.get("lang") or registry.translator.detect(desc)
    text_en = registry.translator.translate(desc, lang)
    rs = allocation.load_ruleset(db)
    cls = allocation.classify(text_en + " " + (desc if lang != "en" else ""), rs, forced_category=f["category"])
    sev = f.get("severity") or cls.severity
    sev_reason = f.get("severity_reason") or cls.severity_reason
    sub = f.get("subcategory") or cls.subcategory
    # duplicate service request check (FRS 3.2 #10)
    if f.get("service_request_no") and not f.get("allow_dup"):
        dup = db.query(Ticket).filter(Ticket.service_request_no == f["service_request_no"], Ticket.category == f["category"],
                                      Ticket.status.in_(R.OPEN_STATUSES)).first()
        if dup:
            raise HTTPException(409, {"message": f"A grievance is already registered against this Service Request Number ({dup.ticket_no}).", "ticket_no": dup.ticket_no})
    policy = pick_policy(db, f["category"], sev)
    # TAT rule (FRS 3.2 #16-18) behind a flag
    if not cfg(db, "allow_pre_breach_filing") and f["category"] == "flight" and sev != 1 and not created_at:
        sr = f.get("sr_logged_at")
        if sr and (now - sr) < timedelta(hours=policy.e1_hours):
            raise HTTPException(422, {"message": f"Grievance can be filed only after the standard TAT of {policy.e1_hours:.0f}h has elapsed (unless critical).", "fields": ["sr_logged_at"]})
    cls.entities.update({k: v for k, v in (("airport_code", None),) if v})
    airport_id = f.get("airport_id")
    if not airport_id and cls.entities.get("airport_code"):
        ap = db.query(Airport).filter(Airport.code == cls.entities["airport_code"]).first()
        airport_id = ap.id if ap else None
    if f.get("assigned_org_id"):
        org = db.get(Organisation, f["assigned_org_id"])
    else:
        org = allocation.route(db, cls, airport_id=airport_id, airline_org_id=f.get("airline_org_id"))
    start_level = allocation.start_level_for(sev)
    airline_org_id = f.get("airline_org_id")
    if not airline_org_id and cls.entities.get("airline_code"):
        a = db.query(Organisation).filter(Organisation.code == cls.entities["airline_code"]).first()
        airline_org_id = a.id if a else None
    t = Ticket(
        user_id=user.id if user else f.get("user_id"), contact_name=f.get("contact_name") or (user.name if user else None),
        contact_mobile=f.get("contact_mobile"), contact_email=f.get("contact_email"), category=f["category"], subcategory=sub,
        description=desc, description_en=text_en, lang=lang, airline_org_id=airline_org_id, airport_id=airport_id,
        flight_no=f.get("flight_no") or cls.entities.get("flight_no"), pnr=f.get("pnr") or cls.entities.get("pnr"),
        service_request_no=f.get("service_request_no") or cls.entities.get("service_request_no"), event_at=f.get("event_at"),
        severity=sev, severity_reason=sev_reason, status="Under Assessment", source_channel=f.get("source_channel", "portal"),
        source_type=f.get("source_type"), social_post_id=f.get("social_post_id"), social_handle=f.get("social_handle"),
        assigned_org_id=org.id if org else None, level=start_level, start_level=start_level, queue="redressor",
        sla_policy_id=policy.id if policy else None, created_at=now, updated_at=now, sla_start=now,
        due_at=now + timedelta(hours=policy.e1_hours) if policy else None, sentiment=cls.sentiment, confidence=f.get("confidence", cls.confidence),
        team=(org.name + " - " + ("Helpdesk" if start_level == 1 else "Senior desk")) if org else None, extra=f.get("extra") or {},
    )
    t.extra = {**t.extra, "severity_keywords": cls.severity_keywords, "matched_keywords": cls.matched_keywords, "entities": cls.entities}
    t.ticket_no = next_ticket_no(db, now.year)
    db.add(t)
    db.flush()
    who = actor_label or (actor_name(user) if user else "Complainant")
    add_event(db, t, who, user.role if user else "passenger", "created",
              f"Grievance submitted via {t.source_channel}" + (f"/{t.source_type}" if t.source_type else ""), None, "Under Assessment", at=now)
    add_event(db, t, "AirSewa Allocation Engine", "system", "classified",
              f"Category: {t.category}/{t.subcategory}; {t.severity_reason}; confidence {t.confidence}", data={"scores": cls.scores}, at=now)
    assignee = assign_user(db, t.assigned_org_id, start_level)
    t.assigned_user_id = assignee.id if assignee else None
    t.status = "Assigned"
    add_event(db, t, "AirSewa Allocation Engine", "system", "assigned",
              f"Auto-routed to {org.name if org else 'AAI'} at level L{start_level}" + (f" ({assignee.name})" if assignee else ""),
              "Under Assessment", "Assigned", {"level": start_level}, at=now)
    if notify:
        tat = f"{policy.e1_hours:.0f} hours" if policy else "standard TAT"
        notify_passenger(db, t, f"AirSewa: grievance {t.ticket_no} registered",
                         f"Your grievance has been registered. Ticket ID: {t.ticket_no}. Category: {R.CATEGORIES[t.category].split(' (')[0]}. "
                         f"Priority S{t.severity}. Expected response within {tat}. Track at airsewa.example/track.")
        if assignee:
            registry.notifier.send(db, "inapp", "in-app", f"New S{t.severity} grievance {t.ticket_no}", t.description[:120], ticket_id=t.id, user_id=assignee.id)
        if org and org.has_crm:
            registry.crm.push(db, t)
    audit(db, who, "ticket.create", t.ticket_no, f"S{t.severity} {t.category}/{t.subcategory}")
    bus.publish("tickets", {"type": "created", "ticket_no": t.ticket_no, "severity": t.severity, "category": t.category, "source": t.source_channel})
    return t


# ------------------------------------------------------------------ visibility / serialization
def visible_query(db, user):
    q = db.query(Ticket)
    if user.role == "passenger":
        return q.filter(Ticket.user_id == user.id)
    if user.role in ("redressor", "nodal"):
        q = q.filter((Ticket.assigned_org_id == user.org_id))
        if user.role == "redressor":
            q = q.filter((Ticket.level <= user.level) | (Ticket.assigned_user_id == user.id))
        return q
    return q


def can_view(user, t: Ticket) -> bool:
    if user.role == "passenger":
        return t.user_id == user.id
    if user.role in ("redressor", "nodal"):
        if t.assigned_org_id != user.org_id and user.org_id not in (t.extra_org_ids or []):
            return False
        return user.role == "nodal" or t.level <= user.level or t.assigned_user_id == user.id
    return True


def ticket_out(t: Ticket, viewer: User | None, detail=False) -> dict:
    full_pii = viewer is not None and viewer.role in ("agent", "passenger")
    d = {
        "id": t.id, "ticket_no": t.ticket_no, "category": t.category, "subcategory": t.subcategory, "severity": t.severity,
        "severity_reason": t.severity_reason, "status": t.status, "source_channel": t.source_channel, "source_type": t.source_type,
        "created_at": iso(t.created_at), "due_at": iso(t.due_at), "updated_at": iso(t.updated_at), "level": t.level,
        "assigned_org": t.assigned_org.name if t.assigned_org else None, "assigned_org_code": t.assigned_org.code if t.assigned_org else None,
        "assigned_user": t.assigned_user.name if t.assigned_user else None, "team": t.team,
        "airport": t.airport.code if t.airport else None, "airline": t.airline.name if t.airline else None,
        "flight_no": t.flight_no, "breached": bool(t.breached), "reopen_count": t.reopen_count, "queue": t.queue,
        "escalation_count": t.escalation_count, "lang": t.lang, "description": (t.description if detail else (t.description or "")[:160]),
        "related_count": t.related_count, "parent_id": t.parent_id, "disputed": t.disputed, "csat": t.csat, "sentiment": t.sentiment,
        "first_response_at": iso(t.first_response_at), "resolved_at": iso(t.resolved_at), "pacr_escalated": t.pacr_escalated,
    }
    if detail:
        pol = t.sla_policy_id
        d.update({
            "description_en": t.description_en, "pnr": t.pnr if full_pii or (viewer and viewer.role in ("redressor", "nodal")) else None,
            "service_request_no": t.service_request_no, "event_at": iso(t.event_at),
            "contact_name": t.contact_name if full_pii else mask_name(t.contact_name),
            "contact_mobile": t.contact_mobile if full_pii else mask_mobile(t.contact_mobile),
            "contact_email": t.contact_email if full_pii else mask_email(t.contact_email),
            "social_handle": t.social_handle if (viewer and viewer.role == "agent") else mask_handle(t.social_handle),
            "social_post_id": t.social_post_id, "hold_reason": t.hold_reason, "resolution_text": t.resolution_text,
            "compliance": t.compliance, "downgrade_request": t.downgrade_request, "confidence": t.confidence,
            "extra_org_ids": t.extra_org_ids, "sla_policy_id": pol, "extra": t.extra, "closed_at": iso(t.closed_at),
        })
    return d


def events_out(db, t: Ticket, viewer: User):
    evs = db.query(TicketEvent).filter(TicketEvent.ticket_id == t.id).order_by(TicketEvent.at, TicketEvent.id).all()
    return [{"at": iso(e.at), "actor": e.actor if viewer.role != "passenger" or e.actor_role in ("system", "passenger") else "AirSewa stakeholder",
             "role": e.actor_role, "type": e.type, "note": e.note, "from": e.from_status, "to": e.to_status} for e in evs]
