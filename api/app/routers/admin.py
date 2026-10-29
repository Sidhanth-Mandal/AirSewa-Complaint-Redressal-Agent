import re
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import reference as R
from ..adapters import registry
from ..core import clock, get_db, hash_password, iso
from ..deps import current_user, require
from ..models import (Airport, AllocationRule, AuditLog, CarRule, Config, Draft, Notification, Organisation, SeverityKeyword, SlaPolicy, SocialNotification,
                      SocialPost, Ticket, User, WatchItem)
from ..modules import allocation, sla
from ..modules import grievance as G
from .auth import check_password_policy, detect_identifier

router = APIRouter(prefix="/admin", tags=["admin"])
admin_only = require("admin")


# ------------------------------------------------------------------ allocation rules + severity matrix (no-code configuration)
class RuleIn(BaseModel):
    keyword: str = Field(min_length=2, max_length=80)
    category: str
    subcategory: str
    target_type: str
    target_org_code: str | None = None
    weight: float = 1.0
    active: bool = True


@router.get("/rules")
def rules(u=Depends(require("admin", "agent")), db: Session = Depends(get_db)):
    return {"rules": [{"id": r.id, "keyword": r.keyword, "category": r.category, "subcategory": r.subcategory, "target_type": r.target_type,
                       "target_org_code": r.target_org_code, "weight": r.weight, "active": r.active} for r in db.query(AllocationRule).order_by(AllocationRule.category, AllocationRule.keyword)],
            "severity": [{"id": s.id, "keyword": s.keyword, "severity": s.severity, "active": s.active} for s in db.query(SeverityKeyword).order_by(SeverityKeyword.severity, SeverityKeyword.keyword)]}


@router.post("/rules")
def add_rule(b: RuleIn, u=Depends(admin_only), db: Session = Depends(get_db)):
    if b.category not in R.CATEGORIES:
        raise HTTPException(422, "Invalid category")
    r = AllocationRule(**b.model_dump(), )
    r.keyword = b.keyword.lower().strip()
    db.add(r)
    G.audit(db, u.name, "rule.add", r.keyword, f"{b.category}/{b.subcategory}")
    db.commit()
    allocation.invalidate()
    return {"id": r.id}


@router.put("/rules/{rid}")
def edit_rule(rid: int, b: RuleIn, u=Depends(admin_only), db: Session = Depends(get_db)):
    r = db.get(AllocationRule, rid)
    if not r:
        raise HTTPException(404)
    for k, v in b.model_dump().items():
        setattr(r, k, v.lower().strip() if k == "keyword" else v)
    G.audit(db, u.name, "rule.edit", r.keyword)
    db.commit()
    allocation.invalidate()
    return {"ok": True}


@router.delete("/rules/{rid}")
def del_rule(rid: int, u=Depends(admin_only), db: Session = Depends(get_db)):
    r = db.get(AllocationRule, rid)
    if r:
        G.audit(db, u.name, "rule.delete", r.keyword)
        db.delete(r)
        db.commit()
        allocation.invalidate()
    return {"ok": True}


class SevIn(BaseModel):
    keyword: str = Field(min_length=2, max_length=80)
    severity: int = Field(ge=1, le=4)
    active: bool = True


@router.post("/severity")
def add_sev(b: SevIn, u=Depends(admin_only), db: Session = Depends(get_db)):
    db.add(SeverityKeyword(keyword=b.keyword.lower().strip(), severity=b.severity, active=b.active))
    G.audit(db, u.name, "severity.add", b.keyword, f"S{b.severity}")
    db.commit()
    allocation.invalidate()
    return {"ok": True}


@router.put("/severity/{sid}")
def edit_sev(sid: int, b: SevIn, u=Depends(admin_only), db: Session = Depends(get_db)):
    s = db.get(SeverityKeyword, sid)
    if not s:
        raise HTTPException(404)
    s.keyword, s.severity, s.active = b.keyword.lower().strip(), b.severity, b.active
    G.audit(db, u.name, "severity.edit", s.keyword)
    db.commit()
    allocation.invalidate()
    return {"ok": True}


@router.delete("/severity/{sid}")
def del_sev(sid: int, u=Depends(admin_only), db: Session = Depends(get_db)):
    s = db.get(SeverityKeyword, sid)
    if s:
        G.audit(db, u.name, "severity.delete", s.keyword)
        db.delete(s)
        db.commit()
        allocation.invalidate()
    return {"ok": True}


class TestIn(BaseModel):
    text: str
    category: str | None = None


@router.post("/rules/test")
def test_rules(b: TestIn, u=Depends(require("admin", "agent")), db: Session = Depends(get_db)):
    """Try the engine live from the admin UI (also shows translation)."""
    lang = registry.translator.detect(b.text)
    en = registry.translator.translate(b.text, lang)
    c = allocation.classify(en, allocation.load_ruleset(db), forced_category=b.category)
    return {"lang": lang, "translated": en, **c.as_dict()}


# ------------------------------------------------------------------ SLA policies + CAR rules
class SlaIn(BaseModel):
    name: str
    category: str | None = None
    severity: int | None = None
    e1_hours: float = Field(gt=0)
    e2_hours: float = Field(gt=0)
    e3_hours: float = Field(gt=0)
    warn_pct: float = 0.8
    active: bool = True


@router.get("/sla")
def sla_list(u=Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": p.id, "name": p.name, "category": p.category, "severity": p.severity, "e1_hours": p.e1_hours, "e2_hours": p.e2_hours,
             "e3_hours": p.e3_hours, "warn_pct": p.warn_pct, "active": p.active} for p in db.query(SlaPolicy)]


@router.post("/sla")
def sla_add(b: SlaIn, u=Depends(admin_only), db: Session = Depends(get_db)):
    if not b.e1_hours <= b.e2_hours <= b.e3_hours:
        raise HTTPException(422, "Thresholds must be increasing (L1 <= L2 <= L3)")
    db.add(SlaPolicy(**b.model_dump()))
    G.audit(db, u.name, "sla.add", b.name)
    db.commit()
    return {"ok": True}


@router.put("/sla/{pid}")
def sla_edit(pid: int, b: SlaIn, u=Depends(admin_only), db: Session = Depends(get_db)):
    p = db.get(SlaPolicy, pid)
    if not p:
        raise HTTPException(404)
    if not b.e1_hours <= b.e2_hours <= b.e3_hours:
        raise HTTPException(422, "Thresholds must be increasing (L1 <= L2 <= L3)")
    for k, v in b.model_dump().items():
        setattr(p, k, v)
    G.audit(db, u.name, "sla.edit", p.name, f"{b.e1_hours}/{b.e2_hours}/{b.e3_hours}")
    db.commit()
    return {"ok": True}


@router.get("/car-rules")
def car_list(u=Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": r.id, "code": r.code, "title": r.title, "subcategory": r.subcategory, "rule_type": r.rule_type, "params": r.params, "active": r.active} for r in db.query(CarRule)]


class CarIn(BaseModel):
    params: dict
    active: bool = True


@router.put("/car-rules/{rid}")
def car_edit(rid: int, b: CarIn, u=Depends(admin_only), db: Session = Depends(get_db)):
    r = db.get(CarRule, rid)
    if not r:
        raise HTTPException(404)
    r.params, r.active = b.params, b.active
    G.audit(db, u.name, "car.edit", r.code, str(b.params))
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ demo clock, config
@router.get("/clock")
def clock_get(u=Depends(admin_only)):
    return {"now": iso(clock.now()), "real": iso(clock.real_now()), "offset_hours": round(clock.offset.total_seconds() / 3600, 2)}


class AdvIn(BaseModel):
    hours: float = Field(ge=-1, le=24 * 60)


@router.post("/clock/advance")
def clock_advance(b: AdvIn, u=Depends(admin_only), db: Session = Depends(get_db)):
    """Fast-forward the demo clock and immediately run the SLA sweeper (live escalation demo)."""
    return sla.advance_clock(db, b.hours)


@router.post("/clock/reset")
def clock_reset(u=Depends(admin_only), db: Session = Depends(get_db)):
    clock.offset = timedelta(0)
    G.set_cfg(db, "clock_offset_s", 0)
    G.audit(db, u.name, "clock.reset")
    db.commit()
    return {"ok": True}


@router.post("/sweep")
def sweep_now(u=Depends(admin_only), db: Session = Depends(get_db)):
    return sla.sweep(db)


@router.get("/config")
def config_get(u=Depends(admin_only), db: Session = Depends(get_db)):
    return {k: G.cfg(db, k) for k in R.CONFIG_DEFAULTS}


class CfgIn(BaseModel):
    values: dict


@router.put("/config")
def config_set(b: CfgIn, u=Depends(admin_only), db: Session = Depends(get_db)):
    for k, v in b.values.items():
        if k not in R.CONFIG_DEFAULTS:
            raise HTTPException(422, f"Unknown config key {k}")
        G.set_cfg(db, k, v)
        G.audit(db, u.name, "config.set", k, str(v)[:200])
    db.commit()
    return {"ok": True}


@router.get("/public-config")
def public_config(db: Session = Depends(get_db)):
    return {"crisis_banner": G.cfg(db, "crisis_banner")}


@router.post("/purge-social")
def purge_social(u=Depends(admin_only), db: Session = Depends(get_db)):
    """Data-retention control: delete all simulated social posts, notifications and social drafts."""
    n1 = db.query(SocialPost).delete()
    n2 = db.query(SocialNotification).delete()
    n3 = db.query(Draft).filter(Draft.channel.in_(["social_x", "social_instagram"]), Draft.status != "approved").delete(synchronize_session=False)
    for d in db.query(Draft).filter(Draft.channel.in_(["social_x", "social_instagram"])):
        d.author_handle, d.author_name, d.original_text, d.payload, d.post_id = "[purged]", None, "[purged per retention policy]", None, None
    for t in db.query(Ticket).filter(Ticket.social_handle != None):  # noqa: E711
        t.social_handle = None
    G.audit(db, u.name, "social.purge", "social", f"posts={n1} notifs={n2} drafts={n3}")
    db.commit()
    return {"posts": n1, "notifications": n2, "drafts": n3}


@router.post("/apply-retention")
def apply_retention(u=Depends(admin_only), db: Session = Depends(get_db)):
    days = G.cfg(db, "social_retention_days") or 90
    cut = clock.real_now() - timedelta(days=days)
    n = db.query(SocialPost).filter(SocialPost.created_at < cut).delete()
    db.commit()
    return {"deleted_posts": n, "older_than_days": days}


@router.get("/audit")
def audit_list(limit: int = 100, u=Depends(require("admin")), db: Session = Depends(get_db)):
    rows = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
    anomalies = []
    cut = clock.now() - timedelta(hours=1)
    bulk = db.query(AuditLog).filter(AuditLog.action == "ticket.bulk", AuditLog.at >= cut).count()
    if bulk >= 3:
        anomalies.append("Multiple bulk edits in the last hour")
    return {"items": [{"at": iso(a.at), "actor": a.actor, "action": a.action, "entity": a.entity, "detail": a.detail} for a in rows], "anomalies": anomalies}


@router.get("/notifications")
def notification_log(limit: int = 100, u=Depends(require("admin", "agent")), db: Session = Depends(get_db)):
    rows = db.query(Notification).order_by(Notification.id.desc()).limit(limit).all()
    return [{"at": iso(n.at), "channel": n.channel, "to": n.to, "subject": n.subject, "body": n.body, "ticket_id": n.ticket_id} for n in rows]


# ------------------------------------------------------------------ users & masters
class UserIn(BaseModel):
    name: str = Field(min_length=2)
    email: str
    mobile: str
    designation: str | None = None
    org_id: int | None = None
    role: str = "redressor"
    level: int = 1
    access_type: str = "write"
    backup_email: str | None = None
    backup_mobile: str | None = None
    authorisation_letter: str | None = None
    password: str = "Welcome@123"


def _check_dup(db, email, mobile, exclude=None):
    q = db.query(User).filter((User.email == email) | (User.mobile == mobile))
    if exclude:
        q = q.filter(User.id != exclude)
    d = q.first()
    if d:
        raise HTTPException(409, f"Staff already registered with this {'email' if d.email == email else 'mobile number'} ({d.name})")


@router.post("/users")
def create_user(b: UserIn, u: User = Depends(require("admin", "nodal")), db: Session = Depends(get_db)):
    """Admin creates Nodal Officers (with authorisation letter); Nodal Officer creates staff of own org (org auto-filled)."""
    _, email = detect_identifier(b.email)
    _, mobile = detect_identifier(b.mobile)
    _check_dup(db, email, mobile)
    check_password_policy(b.password)
    if u.role == "nodal":
        if b.role != "redressor":
            raise HTTPException(403, "Nodal officers can create only redressor staff")
        org_id = u.org_id
    else:
        org_id = b.org_id
        if b.role == "nodal":
            if not (b.backup_email and b.backup_mobile and b.designation and org_id):
                raise HTTPException(422, "Nodal Officer needs organisation, designation, backup delegate email and mobile")
            if not b.authorisation_letter:
                raise HTTPException(422, "Upload/attach the authorisation letter from the redressor organisation")
        elif b.role not in ("agent", "manager", "admin", "redressor"):
            raise HTTPException(422, "Invalid role")
    if b.level not in (1, 2, 3):
        raise HTTPException(422, "Access level must be L1, L2 or L3")
    nu = User(name=b.name, email=email, mobile=mobile, designation=b.designation, org_id=org_id, role=b.role, level=b.level, access_type=b.access_type,
              backup_email=b.backup_email, backup_mobile=b.backup_mobile, password_hash=hash_password(b.password), status="active", created_at=clock.now(),
              user_type="Redressor")
    db.add(nu)
    G.audit(db, u.name, "user.create", email, f"{b.role} L{b.level}" + (f" letter={b.authorisation_letter}" if b.authorisation_letter else ""))
    registry.notifier.send(db, "email", email, "AirSewa account created", f"Your account was created. Temporary password issued; change on first login.")
    db.commit()
    return {"id": nu.id}


@router.get("/users")
def list_users(role: str | None = None, u: User = Depends(require("admin", "nodal")), db: Session = Depends(get_db)):
    q = db.query(User).filter(User.role != "passenger") if role is None else db.query(User).filter(User.role == role)
    if u.role == "nodal":
        q = q.filter(User.org_id == u.org_id)
    return [{"id": x.id, "name": x.name, "email": x.email, "mobile": x.mobile, "role": x.role, "level": x.level, "status": x.status, "access_type": x.access_type,
             "org": x.org.name if x.org else None, "org_id": x.org_id, "designation": x.designation, "last_login": iso(x.last_login)} for x in q.order_by(User.org_id, User.role, User.level).limit(500)]


class UserPatch(BaseModel):
    status: str | None = None
    level: int | None = None
    access_type: str | None = None
    reset_password: bool = False


@router.patch("/users/{uid}")
def patch_user(uid: int, b: UserPatch, u: User = Depends(require("admin", "nodal")), db: Session = Depends(get_db)):
    x = db.get(User, uid)
    if not x or (u.role == "nodal" and x.org_id != u.org_id) or x.role == "passenger":
        raise HTTPException(404, "User not found")
    if u.role == "nodal" and x.role != "redressor":
        raise HTTPException(403, "Nodal officers manage only their redressor staff")
    acts = []
    if b.status:
        if b.status not in ("active", "suspended", "disabled"):
            raise HTTPException(422, "Invalid status")
        acts.append(f"status {x.status}->{b.status}")
        x.status = b.status
    if b.level:
        if b.level not in (1, 2, 3):
            raise HTTPException(422, "Invalid level")
        acts.append(f"level L{x.level}->L{b.level}")
        x.level = b.level
    if b.access_type:
        x.access_type = b.access_type
        acts.append(f"access {b.access_type}")
    if b.reset_password:
        x.password_hash, x.failed_logins = hash_password("Welcome@123"), 0
        acts.append("password reset to default (change on next login)")
    G.audit(db, u.name, "user.update", x.email, "; ".join(acts))
    db.commit()
    return {"ok": True}


@router.get("/masters")
def masters(u=Depends(admin_only), db: Session = Depends(get_db)):
    return {"orgs": [{"id": o.id, "code": o.code, "name": o.name, "type": o.type, "handle": o.handle, "has_crm": o.has_crm} for o in db.query(Organisation)],
            "airports": [{"id": a.id, "code": a.code, "name": a.name, "city": a.city, "state": a.state, "handle": a.handle} for a in db.query(Airport)]}


class OrgIn(BaseModel):
    code: str
    name: str
    type: str
    handle: str | None = None
    has_crm: bool = False


@router.post("/masters/org")
def add_org(b: OrgIn, u=Depends(admin_only), db: Session = Depends(get_db)):
    if db.query(Organisation).filter(Organisation.code == b.code).first():
        raise HTTPException(409, "Organisation code exists")
    db.add(Organisation(**b.model_dump()))
    G.audit(db, u.name, "master.org.add", b.code)
    db.commit()
    allocation.invalidate()
    return {"ok": True}


# ------------------------------------------------------------------ watch list
class WatchIn(BaseModel):
    kind: str
    value: str = Field(min_length=2, max_length=80)
    label: str | None = None
    active: bool = True


@router.get("/watchlist")
def watch_list(u=Depends(require("admin", "agent")), db: Session = Depends(get_db)):
    return [{"id": w.id, "kind": w.kind, "value": w.value, "label": w.label, "active": w.active} for w in db.query(WatchItem).order_by(WatchItem.kind, WatchItem.value)]


@router.post("/watchlist")
def watch_add(b: WatchIn, u=Depends(admin_only), db: Session = Depends(get_db)):
    if b.kind not in ("handle", "hashtag", "keyword"):
        raise HTTPException(422, "kind must be handle, hashtag or keyword")
    v = b.value.strip()
    if b.kind == "handle" and not v.startswith("@"):
        v = "@" + v
    if b.kind == "hashtag" and not v.startswith("#"):
        v = "#" + v
    if db.query(WatchItem).filter(WatchItem.kind == b.kind, WatchItem.value.ilike(v)).first():
        raise HTTPException(409, "Already on the watch list")
    db.add(WatchItem(kind=b.kind, value=v, label=b.label, active=b.active))
    G.audit(db, u.name, "watch.add", v)
    db.commit()
    return {"ok": True}


@router.patch("/watchlist/{wid}")
def watch_toggle(wid: int, active: bool, u=Depends(admin_only), db: Session = Depends(get_db)):
    w = db.get(WatchItem, wid)
    if w:
        w.active = active
        G.audit(db, u.name, "watch.toggle", w.value, str(active))
        db.commit()
    return {"ok": True}


@router.delete("/watchlist/{wid}")
def watch_del(wid: int, u=Depends(admin_only), db: Session = Depends(get_db)):
    w = db.get(WatchItem, wid)
    if w:
        G.audit(db, u.name, "watch.delete", w.value)
        db.delete(w)
        db.commit()
    return {"ok": True}
