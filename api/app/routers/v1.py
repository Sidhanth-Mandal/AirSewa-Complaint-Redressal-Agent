"""Versioned public API (RFP 2.5.21) - SANDBOX / SIMULATED: API-key auth, per-key rate limit, usage counters.
Keys are issued by the administrator only (FRS 3.7 #33-34). The sandbox returns dummy-safe, masked data."""
import hashlib
import secrets
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core import clock, get_db, iso
from ..deps import require
from ..models import Config, Ticket
from ..modules import grievance as G

router = APIRouter(tags=["public-api-v1"])
RATE_LIMIT = 30  # requests / minute / key
_hits: dict = defaultdict(deque)


def _hash(k: str) -> str:
    return hashlib.sha256(k.encode()).hexdigest()


def _keys(db):
    row = db.get(Config, "api_keys")
    return list(row.value) if row and row.value else []


def api_key_auth(x_api_key: str = Header(None), db: Session = Depends(get_db)):
    if not x_api_key:
        raise HTTPException(401, "Missing X-API-Key header")
    keys = _keys(db)
    k = next((k for k in keys if k["hash"] == _hash(x_api_key) and k.get("active", True)), None)
    if not k:
        raise HTTPException(401, "Invalid API key")
    q = _hits[k["hash"]]
    now = time.time()
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise HTTPException(429, f"Rate limit exceeded ({RATE_LIMIT}/min)")
    q.append(now)
    for x in keys:
        if x["hash"] == k["hash"]:
            x["calls"] = x.get("calls", 0) + 1
            x["last_used"] = iso(clock.now())
    G.set_cfg(db, "api_keys", keys)
    db.commit()
    return k


@router.get("/v1/tickets/{ticket_no}", summary="Status of a grievance (sandbox, masked)")
def v1_ticket(ticket_no: str, k=Depends(api_key_auth), db: Session = Depends(get_db)):
    t = db.query(Ticket).filter(Ticket.ticket_no == ticket_no).first()
    if not t:
        raise HTTPException(404, "Not found")
    return {"ticket_no": t.ticket_no, "status": t.status, "severity": f"S{t.severity}", "category": t.category, "subcategory": t.subcategory,
            "assigned_org": t.assigned_org.code if t.assigned_org else None, "created_at": iso(t.created_at), "sla_breached": bool(t.breached), "sandbox": True}


@router.get("/v1/stats", summary="Aggregate counts (sandbox)")
def v1_stats(k=Depends(api_key_auth), db: Session = Depends(get_db)):
    from sqlalchemy import func
    rows = db.query(Ticket.status, func.count()).group_by(Ticket.status).all()
    return {"by_status": dict(rows), "sandbox": True}


class KeyIn(BaseModel):
    name: str


@router.post("/admin/api-keys", summary="Admin: issue an API key (shown once)")
def issue(b: KeyIn, u=Depends(require("admin")), db: Session = Depends(get_db)):
    raw = "asw_" + secrets.token_urlsafe(24)
    keys = _keys(db)
    keys.append({"name": b.name[:60], "hash": _hash(raw), "prefix": raw[:8], "created_at": iso(clock.now()), "calls": 0, "active": True})
    G.set_cfg(db, "api_keys", keys)
    G.audit(db, u.name, "apikey.issue", b.name)
    db.commit()
    return {"key": raw, "note": "Store this key now; only its hash is kept."}


@router.get("/admin/api-keys", summary="Admin: key list and usage")
def list_keys(u=Depends(require("admin")), db: Session = Depends(get_db)):
    return [{k: v for k, v in x.items() if k != "hash"} | {"id": x["hash"][:8], "last_minute": len(_hits.get(x["hash"], []))} for x in _keys(db)]


@router.delete("/admin/api-keys/{kid}")
def revoke(kid: str, u=Depends(require("admin")), db: Session = Depends(get_db)):
    keys = _keys(db)
    for x in keys:
        if x["hash"].startswith(kid):
            x["active"] = False
    G.set_cfg(db, "api_keys", keys)
    G.audit(db, u.name, "apikey.revoke", kid)
    db.commit()
    return {"ok": True}
