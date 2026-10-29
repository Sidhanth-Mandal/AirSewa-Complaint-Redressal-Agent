import asyncio
import json
import re
import threading
import time
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..adapters import registry
from ..core import SessionLocal, UPLOAD_DIR, bus, clock, get_db, iso
from ..deps import current_user, optional_user, require
from ..models import Draft, SocialNotification, SocialPost, SocialUser, Ticket, User, WatchItem
from ..modules import grievance as G
from ..modules import social as S

router = APIRouter(tags=["social"])
SIM_DIR = UPLOAD_DIR / "sim"
SIM_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------ SSE
@router.get("/stream")
async def stream(request: Request, topics: str = "social_feed", u: User | None = Depends(optional_user)):
    want = {t.strip() for t in topics.split(",") if t.strip()}
    staff = u is not None and u.role in ("agent", "admin", "manager", "nodal", "redressor")
    allowed = {t for t in want if t.startswith("social_feed") or t.startswith("social_notif") or (staff and t in ("pacr", "tickets", "social_pulse"))}
    if not allowed:
        raise HTTPException(401, "Login as a staff user to subscribe to these topics")
    entry = bus.subscribe(allowed)
    q = entry[0]

    async def gen():
        try:
            yield "retry: 2000\n\n"
            yield f"event: ready\ndata: {json.dumps({'topics': sorted(allowed)})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    topic, data = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"event: {topic.split(':')[0]}\ndata: {json.dumps({'topic': topic, **data}, default=str)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            bus.unsubscribe(entry)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no", "Connection": "keep-alive"})


# ------------------------------------------------------------------ simulator (public, simulated)
def user_out(x: SocialUser):
    return {"handle": x.handle, "name": x.name, "color": x.color, "lang": x.lang, "bio": x.bio, "is_official": x.is_official, "followers": x.followers}


@router.get("/sim/users")
def sim_users(db: Session = Depends(get_db)):
    us = db.query(SocialUser).order_by(SocialUser.is_official, SocialUser.id).all()
    return {"users": [user_out(x) for x in us if not x.is_official], "officials": [user_out(x) for x in us if x.is_official], "simulated": True}


@router.get("/sim/feed")
def sim_feed(platform: str = "X", limit: int = 40, before_id: int | None = None, db: Session = Depends(get_db)):
    types = ["post", "quote"] if platform == "X" else ["post"]
    q = db.query(SocialPost).filter(SocialPost.platform == platform, SocialPost.source_type.in_(types))
    if before_id:
        q = q.filter(SocialPost.id < before_id)
    return [S.post_out(p) for p in q.order_by(SocialPost.created_at.desc(), SocialPost.id.desc()).limit(min(limit, 100))]


@router.get("/sim/posts/{pid}")
def sim_post(pid: int, db: Session = Depends(get_db)):
    p = db.get(SocialPost, pid)
    if not p:
        raise HTTPException(404)
    replies = db.query(SocialPost).filter(SocialPost.parent_post_id == pid, SocialPost.source_type.in_(["reply", "comment"])).order_by(SocialPost.created_at).limit(200).all()
    return {"post": S.post_out(p), "replies": [S.post_out(r) for r in replies]}


@router.get("/sim/stories")
def sim_stories(db: Session = Depends(get_db)):
    return [S.post_out(p) for p in db.query(SocialPost).filter(SocialPost.source_type == "story_mention").order_by(SocialPost.created_at.desc()).limit(20)]


@router.get("/sim/dm")
def sim_dm(handle: str, db: Session = Depends(get_db)):
    ps = db.query(SocialPost).filter(SocialPost.source_type == "dm", (SocialPost.author_handle == handle) | (SocialPost.target_handle == handle)).order_by(SocialPost.created_at).limit(200).all()
    return [S.post_out(p) for p in ps]


@router.get("/sim/notifications")
def sim_notifs(handle: str, mark_read: bool = False, db: Session = Depends(get_db)):
    ns = db.query(SocialNotification).filter(SocialNotification.handle == handle).order_by(SocialNotification.at.desc()).limit(50).all()
    out = [{"id": n.id, "kind": n.kind, "text": n.text, "from": n.from_handle, "ticket_no": n.ticket_no, "post_id": n.post_id, "at": iso(n.at), "read": n.read} for n in ns]
    if mark_read:
        for n in ns:
            n.read = True
        db.commit()
    return out


@router.post("/sim/media")
async def sim_media(file: UploadFile = File(...)):
    ext = ("." + file.filename.rsplit(".", 1)[-1].lower()) if file.filename and "." in file.filename else ""
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        raise HTTPException(422, "Only images allowed")
    data = await file.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(413, "Image too large (max 5 MB)")
    name = f"{uuid.uuid4().hex}{ext}"
    (SIM_DIR / name).write_bytes(data)
    return {"kind": "upload", "name": file.filename, "url": f"/files/sim/{name}"}


@router.get("/files/sim/{name}")
def sim_file(name: str):
    p = SIM_DIR / re.sub(r"[^A-Za-z0-9._-]", "", name)
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


class PostIn(BaseModel):
    platform: str
    source_type: str = "post"
    author_handle: str
    text: str = Field(min_length=1, max_length=2200)
    media: list[dict] = []
    location: str | None = None
    parent_post_id: int | None = None
    target_handle: str | None = None


def parse_entities(text: str):
    mentions = [m.rstrip(".") for m in re.findall(r"@[A-Za-z0-9_.]+", text)]
    tags = re.findall(r"#[\w\u0900-\u097f]+", text)
    return mentions, tags


def make_post(db, b: PostIn, now=None, seeded=False) -> SocialPost:
    if b.platform not in ("X", "Instagram"):
        raise HTTPException(422, "platform must be X or Instagram")
    allowed = {"X": ["post", "reply", "quote", "dm"], "Instagram": ["post", "comment", "story_mention", "dm"]}[b.platform]
    if b.source_type not in allowed:
        raise HTTPException(422, f"source_type for {b.platform} must be one of {allowed}")
    if b.platform == "X" and len(b.text) > 280:
        raise HTTPException(422, "Post exceeds 280 characters")
    au = db.query(SocialUser).filter(SocialUser.handle == b.author_handle).first()
    if not au:
        raise HTTPException(404, "Unknown simulated user")
    mentions, tags = parse_entities(b.text)
    p = SocialPost(platform=b.platform, source_type=b.source_type, author_handle=au.handle, author_name=au.name, text=b.text,
                   created_at=now or clock.real_now(), lang=registry.translator.detect(b.text), mentions=mentions, hashtags=tags, media=b.media or [],
                   location=b.location, parent_post_id=b.parent_post_id, target_handle=b.target_handle, seeded=seeded)
    db.add(p)
    db.flush()
    p.url = f"/simulator?post={p.id}"
    if b.parent_post_id:
        par = db.get(SocialPost, b.parent_post_id)
        if par:
            if b.source_type == "quote":
                par.reposts += 1
            else:
                par.replies += 1
            if not b.target_handle and b.source_type in ("comment", "reply"):
                p.target_handle = par.author_handle
    return p


def post_ctx(p: SocialPost) -> dict:
    # implicit mention: comment/DM/story to an account counts as addressing it (for watch-list matching)
    ments = list(p.mentions or [])
    if p.target_handle and p.target_handle not in ments:
        ments.append(p.target_handle)
    return {"channel": "social_x" if p.platform == "X" else "social_instagram", "source_type": p.source_type, "text": p.text, "author_handle": p.author_handle,
            "author_name": p.author_name, "post_id": p.id, "parent_post_id": p.parent_post_id, "mentions": ments, "hashtags": p.hashtags or [], "media": p.media or []}


def handle_social_post(payload: dict):
    """Adapter callback: runs the detection pipeline for a freshly created simulated post (own DB session)."""
    with SessionLocal() as db:
        p = db.get(SocialPost, payload["id"])
        d = S.run_pipeline(db, post_ctx(p))
        db.commit()
        return S.draft_out(d, None) if d.id else {"status": "ignored", "reason": d.reason, "timings": d.timings, "total_ms": d.total_ms, "is_complaint": False}


def register_adapters():
    for ad in registry.social.values():
        ad.on_post(handle_social_post)
        ad.start()


def submit_post(b: PostIn):
    """Create the post, publish to feed, and push it through the platform adapter (instant, no polling)."""
    with SessionLocal() as db:
        p = make_post(db, b)
        db.commit()
        out = S.post_out(p)
        pid = p.id
        platform = p.platform
    bus.publish("social_feed", {"type": "post", "post": out})
    t0 = time.perf_counter()
    res = registry.social[platform].emit({"id": pid})
    det = res[0] if res else None
    return {"post": out, "detection": det, "pipeline_ms": round((time.perf_counter() - t0) * 1000, 1)}


@router.post("/sim/posts")
def sim_post_create(b: PostIn):
    return submit_post(b)


def _engage(pid: int, field: str):
    with SessionLocal() as db:
        p = db.get(SocialPost, pid)
        if not p:
            raise HTTPException(404)
        setattr(p, field, (getattr(p, field) or 0) + 1)
        root = db.query(Draft).filter(Draft.post_id == (p.parent_post_id if p.parent_post_id and p.source_type in ("reply", "comment") else p.id)).first()
        d = db.query(Draft).filter(Draft.post_id == p.id).first() or root
        if d:
            d = db.get(Draft, d.parent_draft_id) if d.parent_draft_id else d
            S.update_virality(db, d)
        db.commit()
        out = S.post_out(p)
    bus.publish("social_feed", {"type": "engagement", "post": out})
    return out


@router.post("/sim/posts/{pid}/like")
def sim_like(pid: int):
    return _engage(pid, "likes")


@router.post("/sim/posts/{pid}/repost")
def sim_repost(pid: int):
    return _engage(pid, "reposts")


# ------------------------------------------------------------------ replay (hands-free demo)
REPLAY = [
    ("X", "post", "@rahul_travels", "@IndiGo6E flight 6E 204 DEL-BOM delayed by 4 hours, no announcements, no water. PNR XK92LM. Pathetic service! #flightdelay @MoCA_GoI", None),
    ("X", "post", "@sunita_devi", "@AAI_Official मेरा सामान एयरपोर्ट पर खो गया और उसमें दवाई थी। कृपया मदद करें #AirSewa", None),
    ("X", "post", "@amitbhai99", "@airindia bhai refund nahi mila abhi tak 3 hafte se, PNR QW7R2T. kab milega? #refund", None),
    ("X", "post", "@techie_arjun", "Cheap flights to Dubai! Use code FLY50 for 50% off, click here bit.ly/xyz @airindia", None),
    ("X", "post", "@priya_sharma_", "Thank you @AkasaAir for the smooth flight and lovely crew today, great service! #AirSewa", None),
    ("Instagram", "post", "@meera.flies", "Washrooms at Terminal 3 are so dirty, no water and a terrible smell. Please fix @AAI_Official @DelhiAirport", "DEL"),
    ("X", "post", "@kabir_wanderer", "@DGCAIndia @CivilAviationMinister my 80 year old father was denied wheelchair assistance at BLR airport. Shameful!! #wheelchair", None),
    ("X", "reply", "@priya_sharma_", "+1 same issue happened to us at BLR yesterday", "$LAST_WHEELCHAIR"),
    ("Instagram", "dm", "@rahul_travels", "Hi, my baggage was damaged on 6E 512 BOM-BLR. Broken wheel and torn bag, PNR ZT4K8P. Need compensation.", "@AirSewa_Official"),
    ("Instagram", "story_mention", "@meera.flies", "Stuck at Hyderabad airport for 6 hours, no food no water, kids crying @airindia @MoCA_GoI", "@airindia"),
]
_replay = {"running": False, "step": 0, "total": len(REPLAY)}


def _run_replay(delay: float):
    _replay.update(running=True, step=0)
    last = {}
    try:
        for i, (plat, typ, author, text, extra) in enumerate(REPLAY):
            _replay["step"] = i + 1
            kw = {}
            if typ == "reply" and extra == "$LAST_WHEELCHAIR":
                kw["parent_post_id"] = last.get("wheel")
            elif typ in ("dm", "story_mention"):
                kw["target_handle"] = extra
            elif extra:
                kw["location"] = extra
            res = submit_post(PostIn(platform=plat, source_type=typ, author_handle=author, text=text, **kw))
            if "wheelchair" in text and typ == "post":
                last["wheel"] = res["post"]["id"]
            time.sleep(delay)
    finally:
        _replay["running"] = False


@router.post("/sim/replay")
def sim_replay(delay: float = 3.0):
    if _replay["running"]:
        return {"started": False, **_replay}
    threading.Thread(target=_run_replay, args=(max(0.5, min(delay, 15)),), daemon=True).start()
    return {"started": True, **_replay}


@router.get("/sim/replay")
def sim_replay_status():
    return _replay


# ------------------------------------------------------------------ PACR draft queue
agent_only = require("agent")


@router.get("/pacr/drafts")
def drafts(status: str | None = None, channel: str | None = None, q: str | None = None, limit: int = 100, u: User = Depends(require("agent", "admin", "manager")), db: Session = Depends(get_db)):
    qq = db.query(Draft)
    if status == "queue":
        qq = qq.filter(Draft.status.in_(["pending", "grouped"]), Draft.parent_draft_id == None)  # noqa: E711
    elif status == "filtered":
        qq = qq.filter(Draft.status == "filtered")
    elif status:
        qq = qq.filter(Draft.status == status)
    if channel:
        qq = qq.filter(Draft.channel == channel)
    if q:
        qq = qq.filter(Draft.original_text.ilike(f"%{q}%"))
    rows = qq.order_by(Draft.id.desc()).limit(min(limit, 300)).all()
    rows.sort(key=lambda d: (0 if (d.priority_boost or d.severity == 1) and d.status == "pending" else 1, d.severity if d.status == "pending" else 9, -d.id))
    return [S.draft_out(d, u) for d in rows]


@router.get("/pacr/drafts/{did}")
def draft_detail(did: int, u: User = Depends(require("agent", "admin", "manager")), db: Session = Depends(get_db)):
    d = db.get(Draft, did)
    if not d:
        raise HTTPException(404)
    kids = db.query(Draft).filter(Draft.parent_draft_id == d.id).order_by(Draft.created_at).all()
    return {**S.draft_out(d, u), "children": [S.draft_out(k, u) for k in kids]}


class ApproveIn(BaseModel):
    category: str | None = None
    subcategory: str | None = None
    severity: int | None = None
    assigned_org_id: int | None = None
    airport_id: int | None = None
    force_new: bool = False


@router.post("/pacr/drafts/{did}/approve")
def approve(did: int, b: ApproveIn, u: User = Depends(agent_only), db: Session = Depends(get_db)):
    d = db.get(Draft, did)
    if not d:
        raise HTTPException(404)
    t = S.approve(db, d, u, b.model_dump())
    db.commit()
    return {"ticket_no": t.ticket_no, "ticket_id": t.id, "reply_text": d.reply_text}


class RejectIn(BaseModel):
    reason: str = "Not a valid grievance"


@router.post("/pacr/drafts/{did}/reject")
def reject(did: int, b: RejectIn, u: User = Depends(agent_only), db: Session = Depends(get_db)):
    d = db.get(Draft, did)
    if not d:
        raise HTTPException(404)
    S.reject(db, d, u, b.reason)
    db.commit()
    return {"ok": True}


class ReplyIn(BaseModel):
    text: str | None = None


@router.post("/pacr/drafts/{did}/reply")
def reply(did: int, b: ReplyIn, u: User = Depends(agent_only), db: Session = Depends(get_db)):
    d = db.get(Draft, did)
    if not d:
        raise HTTPException(404)
    S.send_reply(db, d, u, b.text)
    db.commit()
    return {"ok": True, "reply": d.reply_text}


class MergeIn(BaseModel):
    target_draft_id: int | None = None
    target_ticket_no: str | None = None


@router.post("/pacr/drafts/{did}/merge")
def merge(did: int, b: MergeIn, u: User = Depends(agent_only), db: Session = Depends(get_db)):
    """Agent-confirmed merge of a duplicate draft into a parent draft or an existing ticket (RFP 2.5.11 #3)."""
    d = db.get(Draft, did)
    if not d or d.status not in ("pending", "grouped"):
        raise HTTPException(409, "Draft cannot be merged")
    if b.target_draft_id:
        par = db.get(Draft, b.target_draft_id)
        if not par or par.id == d.id:
            raise HTTPException(422, "Invalid target draft")
        d.parent_draft_id, d.status = par.id, "grouped"
        par.related_count = (par.related_count or 0) + 1
        if par.ticket_id:
            tk = db.get(Ticket, par.ticket_id)
            tk.related_count = par.related_count
            G.add_event(db, tk, G.actor_name(u), "agent", "merged", f"Related {d.channel} item merged: {d.original_text[:80]}")
        S.update_virality(db, par)
    elif b.target_ticket_no:
        tk = db.query(Ticket).filter(Ticket.ticket_no == b.target_ticket_no).first()
        if not tk:
            raise HTTPException(404, "Ticket not found")
        d.status, d.ticket_id, d.ticket_no, d.handled_by = "grouped", tk.id, tk.ticket_no, u.name
        tk.related_count = (tk.related_count or 0) + 1
        G.add_event(db, tk, G.actor_name(u), "agent", "merged", f"Duplicate {d.channel} item merged by agent: {d.original_text[:80]}")
        bus.publish("pacr", {"type": "draft_update", "draft": S.draft_out(d, None)})
    else:
        raise HTTPException(422, "Provide target_draft_id or target_ticket_no")
    G.audit(db, u.name, "draft.merge", str(d.id))
    db.commit()
    return {"ok": True}


class BulkDraft(BaseModel):
    ids: list[int]
    action: str
    reason: str = "Bulk rejected"
    severity: int | None = None


@router.post("/pacr/drafts/bulk")
def bulk_drafts(b: BulkDraft, u: User = Depends(agent_only), db: Session = Depends(get_db)):
    n = 0
    for d in db.query(Draft).filter(Draft.id.in_(b.ids[:200])).all():
        try:
            if b.action == "approve":
                S.approve(db, d, u, {"severity": b.severity} if b.severity else {})
            elif b.action == "reject":
                S.reject(db, d, u, b.reason)
            elif b.action == "severity" and b.severity:
                d.severity = b.severity
            else:
                continue
            n += 1
        except HTTPException:
            continue
    db.commit()
    return {"updated": n}


@router.get("/pacr/stats")
def pacr_stats(u: User = Depends(require("agent", "admin", "manager")), db: Session = Depends(get_db)):
    return S.live_stats(db)


# ------------------------------------------------------------------ other PACR channels (simulated)
class ChannelIn(BaseModel):
    sender: str = Field(min_length=3)  # mobile / e-mail / registration no
    name: str | None = None
    text: str = Field(min_length=5)
    subject: str | None = None
    extra: dict = {}


CH_MAP = {"whatsapp": "WhatsApp message", "email": "E-mail", "ivr": "IVR call transcript", "cpgrams": "CPGRAMS record", "letter": "Physical letter (scanned)"}


@router.post("/channels/{channel}")
def channel_ingest(channel: str, b: ChannelIn, u: User = Depends(require("agent", "admin")), db: Session = Depends(get_db)):
    if channel not in CH_MAP:
        raise HTTPException(404, "Unknown channel")
    text = (b.subject + ". " if b.subject else "") + b.text
    note = {"letter": "Text extracted by simulated OCR from scanned letter", "ivr": "Transcribed by simulated speech-to-text"}.get(channel)
    d = S.run_pipeline(db, {"channel": channel, "source_type": channel, "text": text, "author_handle": b.sender, "author_name": b.name, "skip_relevance": True,
                            "payload": {"from": b.sender, "subject": b.subject, "note": note, **b.extra}})
    if note:
        d.media_note = note + " (Simulated)"
    db.commit()
    return S.draft_out(d, u)
