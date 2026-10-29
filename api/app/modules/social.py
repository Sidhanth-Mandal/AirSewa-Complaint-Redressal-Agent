"""Social listening + PACR multi-channel ingestion pipeline (RFP 2.5.35, Annexure-II).
Stages: received -> relevance filter -> language/translate -> classify (shared allocation engine) -> dedup/virality -> draft ticket.
Every stage records its duration in ms so the Live Feed can show the pipeline timeline."""
import re
from datetime import timedelta
from time import perf_counter

from fastapi import HTTPException

from .. import reference as R
from ..adapters import registry
from ..core import bus, clock, iso, mask_handle
from ..models import (Draft, ProductivityLog, SocialNotification, SocialPost, SocialUser, Ticket, WatchItem)
from . import allocation
from . import grievance as G

STOP = set("the a an is are was were to of in on at for and or my me i it this that with from have has had be been not no by as so we our you your pls please".split())
PLUS_ONE = ["+1", "same issue", "same here", "same problem", "me too", "facing the same", "same with me", "happened to me", "exactly same", "same thing"]
CHANNEL_LABEL = {"chat": "Chatbot", "social_x": "X", "social_instagram": "Instagram", "whatsapp": "WhatsApp", "email": "Email", "ivr": "IVR",
                 "cpgrams": "CPGRAMS", "letter": "Letter"}


# ------------------------------------------------------------------------------ watch list
def watch_sets(db):
    items = db.query(WatchItem).filter(WatchItem.active == True).all()  # noqa: E712
    return ({i.value.lower() for i in items if i.kind == "handle"}, {i.value.lower() for i in items if i.kind == "hashtag"},
            [i.value.lower() for i in items if i.kind == "keyword"])


# ------------------------------------------------------------------------------ relevance filter
def relevance(text: str, mentions, hashtags, watch, parent_is_complaint=False) -> dict:
    """Returns {relevant, complaint, reason, matched}. Pure (no DB)."""
    handles, tags, kws = watch
    low = text.lower()
    matched = [m for m in (mentions or []) if m.lower() in handles] + [h for h in (hashtags or []) if h.lower() in tags]
    matched += [k for k in kws if allocation.match(k, low)]
    aviation = [k for k in R.AVIATION_KEYWORDS if allocation.match(k, low)]
    is_plus = parent_is_complaint and any(p in low for p in PLUS_ONE)
    if not matched and not aviation and not parent_is_complaint:
        return {"relevant": False, "complaint": False, "reason": "Not relevant: no watch-list handle/hashtag or aviation keyword", "matched": []}
    if any(p in low for p in R.SPAM_PATTERNS):
        return {"relevant": True, "complaint": False, "reason": "Not a complaint: spam / advertisement", "matched": matched + aviation}
    signals = [s for s in R.COMPLAINT_SIGNALS if allocation.match(s, low)]
    sev_hit = [k for k, s in R.SEVERITY_KEYWORDS if s <= 2 and allocation.match(k, low)]
    sent = allocation.sentiment(text)
    if sent >= 0.2 and not sev_hit:
        return {"relevant": True, "complaint": False, "reason": "Not a complaint: positive feedback", "matched": matched + aviation}
    if any(p in low for p in R.MEME_PATTERNS) and not sev_hit and len({s[:5] for s in signals}) < 2:
        return {"relevant": True, "complaint": False, "reason": "Not a complaint: meme / joke", "matched": matched + aviation}
    if is_plus:
        return {"relevant": True, "complaint": True, "reason": "Related to an existing complaint thread (+1)", "matched": matched + ["thread"], "plus_one": True}
    if not signals and not sev_hit and sent >= -0.1:
        return {"relevant": True, "complaint": False, "reason": "Not a complaint: informational mention, no grievance signal", "matched": matched + aviation}
    return {"relevant": True, "complaint": True, "reason": "Complaint detected: " + ", ".join(signals[:4] or sev_hit[:3] or ["negative sentiment"]),
            "matched": matched + aviation}


# ------------------------------------------------------------------------------ image stub
def image_note(media: list) -> str | None:
    if not media:
        return None
    outs = []
    for m in media:
        n = (m.get("name") or m.get("label") or "").lower()
        if any(k in n for k in ("boarding", "pass")):
            what = "boarding pass (flight & PNR fields detected)"
        elif any(k in n for k in ("bag", "luggage", "suitcase")):
            what = "damaged baggage"
        elif any(k in n for k in ("receipt", "refund", "invoice", "ticket")):
            what = "payment receipt / ticket copy"
        elif any(k in n for k in ("toilet", "washroom", "dirty")):
            what = "unclean washroom"
        elif any(k in n for k in ("queue", "crowd")):
            what = "crowded queue"
        else:
            what = "airport terminal photo"
        outs.append(what)
    return "Evidence attached - OCR/caption (Simulated): " + "; ".join(outs)


# ------------------------------------------------------------------------------ dedup
def _tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP and len(t) > 2}


def jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def find_duplicate(db, ctx: dict, cls, ent: dict, now):
    """Returns (parent_draft | None, dup_ticket | None, reason). Text similarity, same flight, same author, same PNR/SRN, same thread."""
    window = timedelta(hours=G.cfg(db, "dedup_window_hours") or 72)
    thr = G.cfg(db, "dup_similarity") or 0.55
    if ctx.get("parent_post_id"):
        root = db.query(Draft).filter(Draft.post_id == ctx["parent_post_id"], Draft.is_complaint == True).first()  # noqa: E712
        if root:
            root = db.get(Draft, root.parent_draft_id) if root.parent_draft_id else root
            return root, None, "Reply in the same thread as an existing complaint"
    cands = db.query(Draft).filter(Draft.is_complaint == True, Draft.parent_draft_id == None, Draft.created_at >= now - window,  # noqa: E712,E711
                                   Draft.status.in_(["pending", "approved"])).order_by(Draft.id.desc()).limit(400).all()
    best = None
    for c in cands:
        if c.created_at > now:
            continue
        reason, score = None, 0
        ce = c.entities or {}
        if ent.get("pnr") and ce.get("pnr") == ent["pnr"]:
            reason, score = "Same PNR", 1.0
        elif ent.get("service_request_no") and ce.get("service_request_no") == ent["service_request_no"]:
            reason, score = "Same Service Request Number", 1.0
        elif ent.get("flight_no") and ce.get("flight_no") == ent["flight_no"] and c.category == cls.category:
            reason, score = f"Same flight {ent['flight_no']} within window", 0.9
        elif ctx.get("author_handle") and c.author_handle == ctx["author_handle"] and c.category == cls.category and (now - c.created_at) < timedelta(hours=12):
            reason, score = "Same author, same issue (follow-up / repeat post)", 0.8
        else:
            sim = jaccard(ctx["text_en"], c.text_en or "")
            if sim >= thr:
                reason, score = f"Text similarity {sim:.0%}", sim
        if reason and (best is None or score > best[1]):
            best = (c, score, reason)
    if best:
        return best[0], None, best[2]
    # cross-channel duplicate against already-registered tickets (suggest only)
    q = db.query(Ticket).filter(Ticket.status.in_(R.OPEN_STATUSES))
    if ent.get("pnr"):
        t = q.filter(Ticket.pnr == ent["pnr"]).first()
        if t:
            return None, t, f"Open ticket {t.ticket_no} has the same PNR"
    if ent.get("service_request_no"):
        t = q.filter(Ticket.service_request_no == ent["service_request_no"]).first()
        if t:
            return None, t, f"Open ticket {t.ticket_no} has the same Service Request No."
    return None, None, None


# ------------------------------------------------------------------------------ main pipeline
def run_pipeline(db, ctx: dict, publish=True, now=None, seeded=False) -> Draft:
    """ctx: channel, source_type, text, author_handle, author_name, post_id, parent_post_id, mentions, hashtags, media, skip_relevance, payload"""
    t0 = perf_counter()
    now = now or clock.real_now()
    stages = []

    def mark(name, detail=""):
        stages.append({"stage": name, "ms": round((perf_counter() - t0) * 1000, 1), "detail": detail})

    text = ctx["text"]
    mark("received", f"{CHANNEL_LABEL.get(ctx['channel'], ctx['channel'])} / {ctx.get('source_type')}")
    parent_draft = None
    if ctx.get("parent_post_id"):
        p = db.query(Draft).filter(Draft.post_id == ctx["parent_post_id"]).first()
        if p and p.is_complaint:
            parent_draft = p
    lang = registry.translator.detect(text)
    text_en = registry.translator.translate(text, lang)
    if ctx.get("skip_relevance"):
        rel = {"relevant": True, "complaint": True, "reason": "Direct channel: accepted for review", "matched": []}
    else:
        rel = relevance(text_en if lang == "en" else f"{text} {text_en}", ctx.get("mentions"), ctx.get("hashtags"), watch_sets(db),
                        parent_is_complaint=bool(parent_draft))
    mark("filtered", rel["reason"])
    if not rel["relevant"]:
        # Detection triggers only for watch-list / aviation-keyword matches: nothing is stored for unrelated chatter.
        return Draft(id=None, channel=ctx["channel"], status="ignored", is_complaint=False, reason=rel["reason"], timings=stages, total_ms=stages[-1]["ms"],
                     original_text=text, created_at=now)
    d = Draft(channel=ctx["channel"], source_type=ctx.get("source_type"), post_id=ctx.get("post_id"), author_handle=ctx.get("author_handle"),
              author_name=ctx.get("author_name"), original_text=text, created_at=now, seeded=seeded, payload=ctx.get("payload"),
              is_complaint=rel["complaint"], reason=rel["reason"], status="pending" if rel["complaint"] else "filtered", entities={})
    if not rel["complaint"]:
        d.lang = registry.translator.detect(text)
        d.sentiment = allocation.sentiment(text)
        d.text_en = text
        d.timings = stages
        d.total_ms = stages[-1]["ms"]
        db.add(d)
        db.flush()
        if publish:
            bus.publish("pacr", {"type": "draft", "draft": draft_out(d, None)})
        return d

    mark("translated", f"lang={lang}" + (" (mock dictionary)" if lang != "en" else ""))
    rs = allocation.load_ruleset(db)
    cls = allocation.classify(text_en, rs)
    ent = {**cls.entities, **{k: v for k, v in allocation.extract_entities(text, rs.handles).items()}}
    if parent_draft and (rel.get("plus_one") or cls.confidence < 0.5):
        cls.category, cls.subcategory = parent_draft.category, parent_draft.subcategory
        ent = {**(parent_draft.entities or {}), **ent}
    org = allocation.route(db, cls, airline_org_id=None)
    if ent.get("airline_code") and cls.category == "flight":
        from ..models import Organisation
        org = db.query(Organisation).filter(Organisation.code == ent["airline_code"]).first() or org
    mark("classified", f"{cls.category}/{cls.subcategory} S{cls.severity} conf {cls.confidence}")
    ctx["text_en"] = text_en
    dup_parent, dup_ticket, dup_reason = find_duplicate(db, ctx, cls, ent, now)
    mark("deduplicated", dup_reason or "unique")
    from ..models import Airport
    ap = db.query(Airport).filter(Airport.code == ent.get("airport_code")).first() if ent.get("airport_code") else None
    d.lang, d.text_en, d.category, d.subcategory = lang, text_en, cls.category, cls.subcategory
    d.stakeholder, d.stakeholder_org_id = (org.name if org else "AAI"), (org.id if org else None)
    d.airport_id = ap.id if ap else None
    d.severity, d.severity_reason = cls.severity, cls.severity_reason
    d.sentiment, d.confidence, d.entities = cls.sentiment, cls.confidence, ent
    d.media_note = image_note(ctx.get("media") or [])
    if dup_ticket:
        d.dup_of_ticket_id, d.dup_reason = dup_ticket.id, dup_reason
    if dup_parent:
        d.parent_draft_id = dup_parent.id
        d.dup_reason = dup_reason
        d.status = "grouped"
        dup_parent.related_count = (dup_parent.related_count or 0) + 1
        if dup_parent.ticket_id:
            tk = db.get(Ticket, dup_parent.ticket_id)
            tk.related_count = dup_parent.related_count
            G.add_event(db, tk, "Social Listening", "system", "related_post",
                        f"Related {CHANNEL_LABEL.get(d.channel)} post linked ({dup_reason}): {text[:100]}")
    if d.severity == 1:
        d.priority_boost = True
    d.reply_text = default_reply(d, None)
    mark("draft_created", "grouped under parent draft" if dup_parent else "pending agent review")
    d.timings = stages
    d.total_ms = stages[-1]["ms"]
    db.add(d)
    db.flush()
    if dup_parent:
        update_virality(db, dup_parent, publish=publish)
    else:
        update_virality(db, d, publish=False)
    if publish:
        bus.publish("pacr", {"type": "draft", "draft": draft_out(d, None)})
        if dup_parent:
            bus.publish("pacr", {"type": "draft_update", "draft": draft_out(dup_parent, None)})
        bus.publish("social_pulse", {"type": "draft", "channel": d.channel})
    return d


def update_virality(db, root: Draft, publish=True):
    """Raise priority when engagement/related volume spikes (viral complaint)."""
    thr = G.cfg(db, "viral_threshold") or 5
    eng = root.related_count or 0
    if root.post_id:
        p = db.get(SocialPost, root.post_id)
        if p:
            eng += (p.reposts or 0) + (p.replies or 0) + (p.likes or 0) // 5
    root.engagement = eng
    if eng >= thr and not root.viral:
        root.viral = True
        root.priority_boost = True
        old = root.severity
        root.severity = max(1, root.severity - 1)
        root.severity_reason = (root.severity_reason or "") + f" | VIRAL: {eng} related posts/engagements -> priority raised S{old}->S{root.severity}"
        if root.ticket_id:
            tk = db.get(Ticket, root.ticket_id)
            if tk and tk.severity > root.severity:
                tk.severity = root.severity
                tk.severity_reason = root.severity_reason
                G.add_event(db, tk, "Social Listening", "system", "priority_raised", f"Viral complaint: priority raised to S{tk.severity}")
        if publish:
            bus.publish("pacr", {"type": "viral", "draft": draft_out(root, None)})
    elif publish and root.viral:
        bus.publish("pacr", {"type": "draft_update", "draft": draft_out(root, None)})


def default_reply(d: Draft, ticket_no):
    tn = ticket_no or "AS-2026-XXXXXX"
    if d.channel == "social_x":
        return f"We have registered your complaint, ticket {tn}. Please DM details (PNR / flight no. / contact). - AirSewa"
    if d.channel == "social_instagram":
        return f"Thank you for reaching out. Your complaint is registered, ticket {tn}. Please DM us your PNR / flight number. - AirSewa"
    return f"We have registered your complaint, ticket {tn}. You can track it on AirSewa."


# ------------------------------------------------------------------------------ output
def _mask_any(h):
    from ..core import mask_email, mask_mobile
    if not h:
        return h
    if h.startswith("@"):
        return mask_handle(h)
    return mask_email(h) if "@" in h else mask_mobile(h)


def draft_out(d: Draft, viewer) -> dict:
    full = viewer is not None and viewer.role == "agent"
    return {
        "id": d.id, "channel": d.channel, "platform": CHANNEL_LABEL.get(d.channel, d.channel), "source_type": d.source_type, "post_id": d.post_id,
        "status": d.status, "is_complaint": d.is_complaint, "reason": d.reason,
        "author_handle": d.author_handle if full else _mask_any(d.author_handle),
        "masked_handle": _mask_any(d.author_handle),
        "author_name": d.author_name if full else None, "original_text": d.original_text, "text_en": d.text_en, "lang": d.lang,
        "category": d.category, "subcategory": d.subcategory, "stakeholder": d.stakeholder, "stakeholder_org_id": d.stakeholder_org_id,
        "airport_id": d.airport_id, "severity": d.severity, "severity_reason": d.severity_reason, "sentiment": d.sentiment,
        "confidence": d.confidence, "entities": d.entities or {}, "media_note": d.media_note, "timings": d.timings or [], "total_ms": d.total_ms,
        "parent_draft_id": d.parent_draft_id, "related_count": d.related_count, "engagement": d.engagement, "viral": d.viral,
        "priority_boost": d.priority_boost, "dup_of_ticket_id": d.dup_of_ticket_id, "dup_reason": d.dup_reason, "ticket_no": d.ticket_no,
        "ticket_id": d.ticket_id, "reply_text": d.reply_text, "reply_sent": d.reply_sent, "created_at": iso(d.created_at),
        "url": f"/simulator?post={d.post_id}" if d.post_id else None, "payload": d.payload if full else None, "handled_by": d.handled_by,
    }


# ------------------------------------------------------------------------------ agent actions
def _productivity(db, agent, kind="email", n=1):
    day = clock.now().strftime("%Y-%m-%d")
    h = clock.now().hour
    shift = "A" if 6 <= h < 14 else "B" if 14 <= h < 22 else "C"
    row = db.query(ProductivityLog).filter(ProductivityLog.agent_id == agent.id, ProductivityLog.day == day, ProductivityLog.shift == shift).first()
    if not row:
        row = ProductivityLog(agent_id=agent.id, day=day, shift=shift, inbound=0, outbound=0, email=0, chat=0)
        db.add(row)
        db.flush()
    setattr(row, kind, (getattr(row, kind) or 0) + n)


def approve(db, d: Draft, agent, overrides: dict | None = None) -> Ticket:
    if d.status not in ("pending", "grouped"):
        raise HTTPException(409, f"Draft already {d.status}")
    o = overrides or {}
    parent_ticket = None
    if d.parent_draft_id:
        par = db.get(Draft, d.parent_draft_id)
        if par and par.ticket_id and not o.get("force_new"):
            parent_ticket = db.get(Ticket, par.ticket_id)
    cat = o.get("category") or d.category or "other"
    ent = d.entities or {}
    f = {"category": cat, "subcategory": o.get("subcategory") or d.subcategory, "description": d.original_text,
         "contact_name": d.author_name, "severity": int(o.get("severity") or d.severity), "severity_reason": d.severity_reason,
         "assigned_org_id": o.get("assigned_org_id") or d.stakeholder_org_id, "airport_id": o.get("airport_id") or d.airport_id,
         "flight_no": ent.get("flight_no"), "pnr": ent.get("pnr"), "service_request_no": ent.get("service_request_no"),
         "lang": d.lang, "source_channel": d.channel, "source_type": d.source_type, "social_post_id": d.post_id,
         "social_handle": d.author_handle if (d.author_handle or "").startswith("@") else None, "confidence": d.confidence, "allow_dup": True,
         "contact_mobile": (payload_get(d, "from") if d.channel in ("whatsapp", "ivr") else None),
         "contact_email": (payload_get(d, "from") if d.channel == "email" else None), "extra": {"draft_id": d.id}}
    if d.severity_reason and o.get("severity") and int(o["severity"]) != d.severity:
        f["severity_reason"] = f"S{o['severity']}: set by agent {agent.name} (auto: {d.severity_reason})"
    if cat == "flight" and not f["flight_no"] and False:
        pass
    t = G.create_ticket(db, f, user=None, notify=True, actor_label=f"AirSewa Agent {agent.name}")
    if parent_ticket:
        t.parent_id = parent_ticket.id
    d.status, d.ticket_id, d.ticket_no, d.handled_by = "approved", t.id, t.ticket_no, agent.name
    d.reply_text = default_reply(d, t.ticket_no)
    G.add_event(db, t, G.actor_name(agent), "agent", "draft_approved",
                f"Approved from {CHANNEL_LABEL.get(d.channel)} draft (AI confidence {d.confidence}); original post: {('/simulator?post=' + str(d.post_id)) if d.post_id else 'n/a'}")
    # grouped children become linked tickets' related posts
    kids = db.query(Draft).filter(Draft.parent_draft_id == d.id).count()
    t.related_count = kids
    if d.viral:
        t.severity = d.severity
    G.audit(db, agent.name, "draft.approve", t.ticket_no, f"draft {d.id}")
    _productivity(db, agent, "email", 1)
    bus.publish("pacr", {"type": "draft_update", "draft": draft_out(d, None)})
    return t


def payload_get(d, key):
    return (d.payload or {}).get(key)


def reject(db, d: Draft, agent, reason: str):
    if d.status not in ("pending", "grouped"):
        raise HTTPException(409, f"Draft already {d.status}")
    d.status, d.handled_by, d.reason = "rejected", agent.name, f"Rejected by agent: {reason}"
    G.audit(db, agent.name, "draft.reject", str(d.id), reason)
    _productivity(db, agent, "email", 1)
    bus.publish("pacr", {"type": "draft_update", "draft": draft_out(d, None)})


def send_reply(db, d: Draft, agent, text: str | None = None):
    """Posts the acknowledgment as the official handle into the simulator (reply / comment / DM) + user's notifications."""
    if d.status != "approved":
        raise HTTPException(409, "Approve the draft (create the ticket) before sending the acknowledgment")
    if d.reply_sent:
        raise HTTPException(409, "Reply already sent")
    body = (text or d.reply_text or default_reply(d, d.ticket_no)).replace("AS-2026-XXXXXX", d.ticket_no or "")
    d.reply_text, d.reply_sent = body, True
    if d.channel in ("social_x", "social_instagram"):
        plat = "X" if d.channel == "social_x" else "Instagram"
        src = {"social_x": "reply"}.get(d.channel) or ("dm" if d.source_type in ("dm", "story_mention") else "comment")
        official = db.query(SocialUser).filter(SocialUser.handle == "@AirSewa_Official").first()
        post = SocialPost(platform=plat, source_type=src, author_handle="@AirSewa_Official", author_name=official.name if official else "AirSewa",
                          text=f"{d.author_handle} {body}" if src == "reply" else body, created_at=clock.real_now(), lang="en",
                          mentions=[d.author_handle] if d.author_handle else [], hashtags=[], media=[], parent_post_id=d.post_id,
                          target_handle=d.author_handle, url="")
        db.add(post)
        db.flush()
        post.url = f"/simulator?post={post.id}"
        src_post = db.get(SocialPost, d.post_id) if d.post_id else None
        if src_post:
            src_post.replies = (src_post.replies or 0) + 1
        db.add(SocialNotification(handle=d.author_handle, kind="reply" if src != "dm" else "dm", text=body, from_handle="@AirSewa_Official",
                                  post_id=post.id, ticket_no=d.ticket_no, at=clock.real_now()))
        bus.publish("social_feed", {"type": "post", "post": post_out(post)})
        bus.publish(f"social_notif:{(d.author_handle or '').lower()}", {"ticket_no": d.ticket_no, "text": body, "kind": "reply"})
    else:
        from ..models import Notification
        db.add(Notification(ticket_id=d.ticket_id, user_id=None, channel={"whatsapp": "whatsapp", "email": "email"}.get(d.channel, "sms"),
                            to=mask_handle(d.author_handle) if d.author_handle else "n/a", subject="Acknowledgment", body=body, at=clock.now()))
    G.audit(db, agent.name, "draft.reply", d.ticket_no or "", body[:100])
    _productivity(db, agent, "email", 1)
    bus.publish("pacr", {"type": "draft_update", "draft": draft_out(d, None)})


def post_out(p: SocialPost, db=None) -> dict:
    return {"id": p.id, "platform": p.platform, "source_type": p.source_type, "author_handle": p.author_handle, "author_name": p.author_name,
            "text": p.text, "created_at": iso(p.created_at), "lang": p.lang, "mentions": p.mentions or [], "hashtags": p.hashtags or [],
            "media": p.media or [], "location": p.location, "parent_post_id": p.parent_post_id, "target_handle": p.target_handle,
            "likes": p.likes, "reposts": p.reposts, "replies": p.replies, "url": p.url}


# ------------------------------------------------------------------------------ stats
def live_stats(db) -> dict:
    now = clock.real_now()
    since5 = now - timedelta(minutes=5)
    q = db.query(Draft).filter(Draft.created_at >= since5)
    detected = q.filter(Draft.is_complaint == True).count()  # noqa: E712
    filtered = q.filter(Draft.is_complaint == False).count()  # noqa: E712
    recent = db.query(Draft.channel, Draft.created_at, Draft.subcategory, Draft.is_complaint).filter(Draft.created_at >= now - timedelta(minutes=30)).all()
    spark = {"social_x": [0] * 30, "social_instagram": [0] * 30}
    for ch, at, _s, ic in recent:
        if ch in spark and ic:
            idx = 29 - int((now - at).total_seconds() // 60)
            if 0 <= idx < 30:
                spark[ch][idx] += 1
    day = db.query(Draft.subcategory, Draft.category).filter(Draft.created_at >= now - timedelta(hours=24), Draft.is_complaint == True).all()  # noqa: E712
    trend: dict = {}
    for s, c in day:
        trend[f"{c}/{s}"] = trend.get(f"{c}/{s}", 0) + 1
    pending = db.query(Draft).filter(Draft.status == "pending").count()
    return {"detected_5m": detected, "filtered_5m": filtered, "pending": pending, "sparkline": spark,
            "trending": sorted(({"issue": k, "count": v} for k, v in trend.items()), key=lambda x: -x["count"])[:6]}
