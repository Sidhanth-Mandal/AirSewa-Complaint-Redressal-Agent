import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..adapters import registry
from ..core import clock, get_db, iso
from ..deps import optional_user, require
from ..models import Config, FlightInfo, Notification, Organisation, Ticket, User
from ..modules import closure, allocation
from ..modules import grievance as G
from ..modules import social as S

router = APIRouter(tags=["misc"])


# ------------------------------------------------------------------ flight tracking (no login)
@router.get("/flights/{flight_no}")
def flight(flight_no: str):
    r = registry.flights.status(flight_no)
    if not r:
        raise HTTPException(404, "Enter a valid flight number, e.g. 6E 204")
    return r


class SubIn(BaseModel):
    flight_no: str
    contact: str
    channel: str = "sms"


@router.post("/flights/subscribe")
def subscribe(b: SubIn, db: Session = Depends(get_db)):
    """Opt in to updates for a flight (SIMULATED: no real SMS/WhatsApp; the message appears in the Notification Log)."""
    st = registry.flights.status(b.flight_no)
    if not st:
        raise HTTPException(404, "Invalid flight number")
    db.add(FlightInfo(flight_no=st["flight_no"], contact=b.contact[:160], channel=b.channel, at=clock.now()))
    registry.notifier.send(db, b.channel if b.channel in ("sms", "email", "whatsapp") else "sms", b.contact, f"Flight {st['flight_no']} update",
                           f"{st['flight_no']} {st['from']}->{st['to']}: {st['status']}" + (f" (delayed {st['delay_minutes']} min)" if st["delay_minutes"] else "") + ". You will receive regular updates.")
    db.commit()
    return {"subscribed": True, "simulated": True}


# ------------------------------------------------------------------ chatbot (deterministic rules; LLM optional)
FAQ = [
    (["refund"], "Refunds: for airline-cancelled flights you are entitled to a full refund of the ticket amount (CAR Sec 3 Series M Part II). Raise a grievance with your PNR if it is delayed.",
     "रिफंड: एयरलाइन द्वारा रद्द की गई उड़ान पर पूरे टिकट का रिफंड मिलता है। देरी होने पर PNR के साथ शिकायत दर्ज करें।"),
    (["baggage", "luggage", "bag"], "Lost or damaged baggage: report to the airline desk before leaving the airport and file an AirSewa grievance with your PNR. Liability is about Rs 350/kg (illustrative).",
     "खोया/क्षतिग्रस्त सामान: एयरपोर्ट छोड़ने से पहले एयरलाइन डेस्क पर रिपोर्ट करें और PNR के साथ AirSewa में शिकायत दर्ज करें।"),
    (["wheelchair", "assistance", "disabled"], "Wheelchair / special assistance is free. Request it with your airline at booking, or raise an 'On-ground' grievance if it was not provided.",
     "व्हीलचेयर/विशेष सहायता निःशुल्क है। बुकिंग के समय एयरलाइन से अनुरोध करें, न मिलने पर 'On-ground' शिकायत दर्ज करें।"),
    (["document", "id", "carry"], "Carry a valid government photo ID for domestic flights. International travellers need a passport (and visa where required).",
     "घरेलू उड़ान के लिए वैध सरकारी फोटो पहचान पत्र साथ रखें। अंतरराष्ट्रीय यात्रा के लिए पासपोर्ट आवश्यक है।"),
    (["escalat", "reopen"], "You can escalate an open grievance, or reopen a resolved one up to 2 times, from the ticket page.",
     "आप खुली शिकायत को एस्केलेट कर सकते हैं, और हल हो चुकी शिकायत को अधिकतम 2 बार दोबारा खोल सकते हैं।"),
]


class ChatIn(BaseModel):
    message: str
    lang: str = "en"
    state: dict = {}


@router.post("/chatbot")
def chatbot(b: ChatIn, u: User | None = Depends(optional_user), db: Session = Depends(get_db)):
    hi = b.lang == "hi"
    m = b.message.strip()
    low = m.lower()
    st = dict(b.state or {})
    qr = ["Track flight", "File a grievance", "Track ticket", "Talk to an agent"] if not hi else ["उड़ान ट्रैक करें", "शिकायत दर्ज करें", "टिकट ट्रैक करें", "एजेंट से बात करें"]

    def out(reply_en, reply_hi, **kw):
        return {"reply": reply_hi if hi else reply_en, "quick_replies": qr, "state": st, "simulated_llm": registry.llm.__class__.__name__ == "NoLLM", **kw}

    # guided filing in progress
    if st.get("flow") == "file":
        if st.get("step") == "describe":
            lang = registry.translator.detect(m)
            c = allocation.classify(registry.translator.translate(m, lang), allocation.load_ruleset(db))
            st = {"flow": None}
            return out(f"I understood this as **{c.category} / {c.subcategory}**, priority **S{c.severity}** ({c.severity_reason}). Tap below to review and submit the form - I have pre-filled it.",
                       f"मैंने इसे **{c.category} / {c.subcategory}**, प्राथमिकता **S{c.severity}** समझा है। नीचे फॉर्म खोलकर जाँच करें और जमा करें।",
                       action={"type": "open_form", "category": c.category, "description": m})
    if re.search(r"\b(agent|human|person|executive)\b|एजेंट|इंसान", low):
        d = S.run_pipeline(db, {"channel": "chat", "source_type": "chat", "text": "Chatbot handoff: " + (st.get("last_user") or m), "author_handle": u.mobile if u and u.mobile else "chat-visitor",
                                "author_name": u.name if u else "Visitor", "skip_relevance": True})
        db.commit()
        return out("I have handed this chat to an AirSewa agent (Simulated live-agent handoff). They will review it in the PACR queue.",
                   "मैंने यह चैट AirSewa एजेंट को सौंप दी है। वे PACR कतार में इसे देखेंगे।", action={"type": "handoff", "draft_id": d.id})
    fm = re.search(r"\b([A-Za-z0-9]{2})\s?-?(\d{2,4})\b", m)
    if fm and re.search(r"flight|status|track|उड़ान|ट्रैक", low) or (fm and allocation.extract_entities(m).get("flight_no")):
        s = registry.flights.status(fm.group(1) + fm.group(2))
        if s:
            return out(f"Flight {s['flight_no']} {s['from']}->{s['to']}: {s['status']}" + (f", delayed {s['delay_minutes']} min" if s['delay_minutes'] else "") + f". Gate {s['gate']}. (Simulated data)",
                       f"उड़ान {s['flight_no']} {s['from']}->{s['to']}: {s['status']}। गेट {s['gate']}। (सिम्युलेटेड डेटा)", action={"type": "flight", "data": s})
    tm = re.search(r"AS-\d{4}-\d{6}", m, re.I)
    if tm:
        t = db.query(Ticket).filter(Ticket.ticket_no == tm.group(0).upper()).first()
        if t and u and (u.role in ("agent", "admin") or t.user_id == u.id):
            return out(f"Ticket {t.ticket_no} is **{t.status}** (priority S{t.severity}).", f"टिकट {t.ticket_no} की स्थिति: **{t.status}**।")
        return out("Please login to view that ticket, or use Track Ticket with your mobile number.", "टिकट देखने के लिए कृपया लॉगिन करें।")
    if re.search(r"file|complain|grievance|शिकायत|दर्ज", low):
        st = {"flow": "file", "step": "describe"}
        return out("Sure. Describe your problem in one or two sentences (English or Hindi), including airline / airport / flight no.", "ठीक है। अपनी समस्या एक-दो वाक्यों में बताएं (हिंदी/अंग्रेज़ी), एयरलाइन/एयरपोर्ट/फ्लाइट नंबर सहित।")
    if re.search(r"track.*flight|flight.*status|उड़ान", low):
        return out("Type the flight number, for example: 6E 204", "उड़ान संख्या लिखें, जैसे: 6E 204")
    if re.search(r"track.*ticket|ticket.*status|टिकट", low):
        return out("Type your ticket ID, for example: AS-2026-000123", "अपना टिकट ID लिखें, जैसे: AS-2026-000123")
    for keys, en, hn in FAQ:
        if any(k in low for k in keys):
            return out(en, hn)
    llm = registry.llm.complete("You are AirSewa assistant for Indian air passengers. Be brief.", m)
    if llm:
        return out(llm, llm)
    st["last_user"] = m
    return out("I can help with flight status, filing and tracking grievances, and FAQs on refunds, baggage and wheelchair assistance. What would you like to do?",
               "मैं उड़ान की स्थिति, शिकायत दर्ज/ट्रैक करने और रिफंड, सामान व व्हीलचेयर संबंधी जानकारी में मदद कर सकता हूँ। आप क्या करना चाहेंगे?")


# ------------------------------------------------------------------ simulated airline CRM (webhook call-to-action + status sync-back)
@router.get("/crm/inbox")
def crm_inbox(org: str | None = None, db: Session = Depends(get_db)):
    row = db.get(Config, "crm_inbox")
    items = list(row.value) if row and row.value else []
    if org:
        items = [i for i in items if i.get("org") == org]
    for i in items:
        t = db.query(Ticket).filter(Ticket.ticket_no == i["ticket_no"]).first()
        i["airsewa_status"] = t.status if t else None
        i["subcategory"] = t.subcategory if t else i.get("subcategory")
        i["severity"] = t.severity if t else None
    return {"items": items[::-1], "simulated": True}


class CrmUpdate(BaseModel):
    status: str  # Acknowledged | Resolved
    amount: float | None = None
    txn_id: str | None = None
    note: str = ""


@router.post("/crm/{ticket_no}/update")
def crm_update(ticket_no: str, b: CrmUpdate, db: Session = Depends(get_db)):
    """The airline CRM calls back with a status; AirSewa syncs it (and auto-closes via the normal closure rules)."""
    t = db.query(Ticket).filter(Ticket.ticket_no == ticket_no).first()
    if not t:
        raise HTTPException(404)
    actor = db.query(User).filter(User.org_id == t.assigned_org_id, User.role == "nodal").first()
    if not actor:
        raise HTTPException(409, "No nodal officer for this organisation")
    msg = {}
    if b.status == "Acknowledged":
        if t.status in ("Assigned", "Reopened", "Escalated"):
            G.transition(db, t, "In-Progress", actor, "Acknowledged in airline CRM (synced)")
    elif b.status == "Resolved":
        if t.status in ("Assigned", "Escalated", "Reopened"):
            G.transition(db, t, "In-Progress", actor, "Acknowledged in airline CRM (synced)")
        msg = closure.resolve(db, t, actor, b.note or "Resolved in airline CRM", {"amount": b.amount, "txn_id": b.txn_id}, True)
    else:
        raise HTTPException(422, "status must be Acknowledged or Resolved")
    row = db.get(Config, "crm_inbox")
    if row:
        row.value = [{**i, "crm_status": b.status} if i["ticket_no"] == ticket_no else i for i in row.value]
    db.commit()
    return {"ok": True, "synced_status": t.status, "compliance": msg}
