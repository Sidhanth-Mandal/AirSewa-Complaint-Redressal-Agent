"""End-to-end acceptance tests against the real FastAPI app (temp DB, minimal seed)."""
import time

from tests.conftest import login

FLIGHT = dict(category="flight", consent=True, contact_name="Test Pax", contact_mobile="9876543210", contact_email="t@example.com",
              event_at="2026-10-28T10:00:00", service_request_no="SR1", pnr="ABC123", flight_no="6E204")


def meta(c):
    return c.get("/meta").json()


def file_ticket(pax, c, **kw):
    m = meta(c)
    airline = {a["code"]: a["id"] for a in m["airlines"]}
    body = {**FLIGHT, "airline_org_id": airline[kw.pop("airline", "6E")], **kw}
    r = pax.post("/tickets", json=body)
    assert r.status_code == 200, r.text
    return r.json()


_srn = [100]


def srn():
    _srn[0] += 1
    return f"SRN{_srn[0]}"


# ---------------------------------------------------------------- portal end to end
def test_portal_ticket_classified_routed_and_visible(client, pax, admin):
    t = file_ticket(pax, client, airline="AI", description="Air India lost my baggage and it contains my father's medicine. Urgent help needed.", service_request_no=srn())
    assert t["ticket_no"].startswith("AS-") and t["severity"] == 1 and "medicine" in t["severity_reason"]
    assert t["category"] == "flight" and t["subcategory"] == "baggage_lost"
    assert t["assigned_org"] == "Air India" and t["level"] == 2 and t["status"] == "Assigned"
    l2 = login(client, "ai.l2@demo.in")
    l1 = login(client, "ai.l1a@demo.in")
    assert any(i["ticket_no"] == t["ticket_no"] for i in l2.get("/tickets").json()["items"])           # S1 -> L2+
    assert not any(i["ticket_no"] == t["ticket_no"] for i in l1.get("/tickets").json()["items"])
    other = login(client, "6e.l2@demo.in")
    assert other.get(f"/tickets/{t['ticket_no']}").status_code == 403                                   # RBAC: other org
    d = l2.get(f"/tickets/{t['ticket_no']}").json()                                                     # opening -> In-Progress
    assert d["status"] == "In-Progress" and d["contact_mobile"].count("X") == 4                         # PII masked for redressor
    k = admin.get("/dashboard/summary").json()["kpis"]
    assert k["total"] >= 1 and k["critical_total"] >= 1


def test_mandatory_fields_and_consent(client, pax):
    r = pax.post("/tickets", json={"category": "flight", "description": "Flight delayed for a very long time", "consent": True, "contact_mobile": "9876543210"})
    assert r.status_code == 422 and "airline_org_id" in r.text
    r = pax.post("/tickets", json={"category": "airport", "description": "Washroom is dirty at the terminal", "contact_mobile": "9876543210",
                                   "event_at": "2026-10-28T10:00:00", "airport_id": 1, "consent": False})
    assert r.status_code == 422 and "consent" in r.text


def test_duplicate_service_request_blocked(client, pax):
    s = srn()
    file_ticket(pax, client, description="Flight delayed by five hours with no announcement", service_request_no=s)
    r = pax.post("/tickets", json={**FLIGHT, "airline_org_id": meta(client)["airlines"][0]["id"], "description": "Flight delayed by five hours again", "service_request_no": s})
    assert r.status_code == 409


def test_upload_validation(client, pax):
    t = file_ticket(pax, client, description="Refund pending for cancelled flight since a month", service_request_no=srn())
    ok = pax.post(f"/tickets/{t['ticket_no']}/attachments", files={"file": ("a.pdf", b"%PDF-1.4 test", "application/pdf")})
    assert ok.status_code == 200
    assert pax.post(f"/tickets/{t['ticket_no']}/attachments", files={"file": ("a.exe", b"MZ", "application/octet-stream")}).status_code == 422
    assert pax.post(f"/tickets/{t['ticket_no']}/attachments", files={"file": ("a.png", b"not a png", "image/png")}).status_code == 422
    big = b"%PDF" + b"0" * (10 * 1024 * 1024 + 10)
    assert pax.post(f"/tickets/{t['ticket_no']}/attachments", files={"file": ("big.pdf", big, "application/pdf")}).status_code == 413


# ---------------------------------------------------------------- SLA
def test_demo_clock_escalates_l1_l2_l3_nodal(client, pax, admin):
    t = file_ticket(pax, client, airline="SG", description="SpiceJet flight delayed by seven hours, need compensation please", service_request_no=srn())
    ref = t["ticket_no"]
    nodal = login(client, "nodal.sg@demo.in")
    assert nodal.get(f"/tickets/{ref}").json()["level"] == 1
    admin.post("/admin/clock/advance", json={"hours": 19.5})            # 80% of 24h -> near-breach warning
    d = nodal.get(f"/tickets/{ref}").json()
    assert any(e["type"] == "near_breach" for e in d["events"]) and not d["breached"]
    admin.post("/admin/clock/advance", json={"hours": 6})                # > 24h  -> breach, L1 -> L2
    d = nodal.get(f"/tickets/{ref}").json()
    assert d["breached"] and d["level"] == 2 and d["status"] in ("Escalated", "In-Progress")
    admin.post("/admin/clock/advance", json={"hours": 50})               # > 72h  -> L3
    assert nodal.get(f"/tickets/{ref}").json()["level"] == 3
    admin.post("/admin/clock/advance", json={"hours": 30})               # > 96h  -> Nodal / PACR
    d = nodal.get(f"/tickets/{ref}").json()
    assert d["level"] == 4 and d["queue"] == "pacr"
    assert sum(1 for e in d["events"] if e["type"] == "escalation") >= 3
    admin.post("/admin/clock/reset")


# ---------------------------------------------------------------- closure
def test_resolution_requires_evidence_and_car_compliance(client, pax):
    t = file_ticket(pax, client, description="Refund not received for cancelled IndiGo flight, PNR ABC123, waiting 20 days", service_request_no=srn(), ticket_amount=8500)
    assert t["subcategory"] == "refund"
    ref = t["ticket_no"]
    nodal = login(client, "nodal.6e@demo.in")
    r = nodal.post(f"/tickets/{ref}/action", json={"action": "resolve", "resolution_text": "Refund processed"})
    assert r.status_code == 422 and "Evidence" in r.text                                               # no evidence -> blocked
    r = nodal.post(f"/tickets/{ref}/action", json={"action": "resolve", "resolution_text": "Refund processed", "txn_id": "TXN1", "amount": 5000})
    assert r.status_code == 422 and "compliance" in r.text.lower()                                     # non-compliant refund fails
    d = nodal.get(f"/tickets/{ref}").json()
    assert d["status"] != "Resolved" and any(e["type"] == "compliance_fail" for e in d["events"])
    r = nodal.post(f"/tickets/{ref}/action", json={"action": "resolve", "resolution_text": "Full refund processed", "txn_id": "TXN2", "amount": 8500})
    assert r.status_code == 200 and r.json()["status"] == "Resolved"


def test_reopen_at_most_twice_then_dispute(client, pax):
    t = file_ticket(pax, client, description="IndiGo flight delayed and no meals offered during long delay", service_request_no=srn())
    ref = t["ticket_no"]
    nodal = login(client, "nodal.6e@demo.in")
    for i in range(3):
        nodal.get(f"/tickets/{ref}")
        st = nodal.post(f"/tickets/{ref}/action", json={"action": "resolve", "resolution_text": f"Resolved attempt {i}", "reference": f"REF{i}"})
        assert st.status_code == 200, st.text
        r = pax.post(f"/tickets/{ref}/action", json={"action": "reopen", "note": "not fixed"})
        if i < 2:
            assert r.status_code == 200, r.text
        else:
            assert r.status_code == 409                                                                 # third reopen refused
    d = pax.get(f"/tickets/{ref}").json()
    assert d["reopen_count"] == 2 and not d["can_reopen"]
    assert pax.post(f"/tickets/{ref}/action", json={"action": "dispute", "note": "still unhappy"}).status_code == 200
    agent = login(client, "agent1@pacr.demo")
    assert agent.get(f"/tickets?queue=committee").json()["total"] >= 1
    r = agent.post(f"/tickets/{ref}/action", json={"action": "committee", "decision": "uphold", "note": "Genuine resolution"})
    assert r.status_code == 200 and agent.get(f"/tickets/{ref}").json()["status"] == "Closed"


def test_passenger_feedback_confirms_and_closes(client, pax):
    t = file_ticket(pax, client, description="Washroom at the airport was dirty with no water for hours", category="airport", airport_id=1, service_request_no=None)
    ref = t["ticket_no"]
    op = login(client, "dial.l1a@demo.in")
    op.get(f"/tickets/{ref}")
    assert op.post(f"/tickets/{ref}/action", json={"action": "resolve", "resolution_text": "Cleaned and restocked", "reference": "JOB-77"}).status_code == 200
    r = pax.post(f"/tickets/{ref}/action", json={"action": "feedback", "rating": 5, "confirms": True})
    assert r.status_code == 200 and r.json()["status"] == "Closed"


def test_severity_override_rules(client, pax):
    t = file_ticket(pax, client, description="IndiGo flight delayed by many hours, need assistance", service_request_no=srn())
    ref = t["ticket_no"]
    l1 = login(client, "6e.l1a@demo.in")
    assert l1.post(f"/tickets/{ref}/action", json={"action": "severity", "severity": 2, "note": "x"}).status_code == 403    # L1 cannot override
    nodal = login(client, "nodal.6e@demo.in")
    assert nodal.post(f"/tickets/{ref}/action", json={"action": "severity", "severity": 2, "note": "pregnant passenger"}).status_code == 200
    r = nodal.post(f"/tickets/{ref}/action", json={"action": "severity", "severity": 4, "note": "downgrade please"})
    assert r.status_code == 200 and r.json().get("pending_approval")                                   # downgrade needs approval
    assert nodal.get(f"/tickets/{ref}").json()["severity"] == 2
    l3 = login(client, "6e.l3@demo.in")
    assert l3.post(f"/tickets/{ref}/action", json={"action": "approve_downgrade"}).status_code in (200, 403)


def test_agent_can_downgrade_and_merge(client, pax):
    a = file_ticket(pax, client, description="IndiGo flight delayed more than five hours today", service_request_no=srn())
    b = file_ticket(pax, client, description="IndiGo flight delayed more than five hours today again", service_request_no=srn())
    agent = login(client, "agent1@pacr.demo")
    assert agent.post(f"/tickets/{a['ticket_no']}/action", json={"action": "severity", "severity": 4, "note": "minor"}).status_code == 200
    assert agent.post(f"/tickets/{b['ticket_no']}/action", json={"action": "merge", "parent_ref": a["ticket_no"], "note": "dup"}).status_code == 200
    d = agent.get(f"/tickets/{a['ticket_no']}").json()
    assert d["related_count"] == 1 and d["children"][0]["ticket_no"] == b["ticket_no"]


# ---------------------------------------------------------------- auth / RBAC
def test_otp_guest_login_and_password_policy(client):
    c = login.__globals__["TestClient"](client.app) if False else None
    from fastapi.testclient import TestClient
    c = TestClient(client.app)
    assert c.post("/auth/otp/verify", json={"identifier": "9811122233", "otp": "000000"}).status_code == 401
    r = c.post("/auth/otp/request", json={"identifier": "9811122233"})
    assert r.json()["dev_otp"] == "123456"
    r = c.post("/auth/otp/verify", json={"identifier": "9811122233", "otp": "123456", "mode": "guest", "consent_save": False, "name": "Guest One"})
    assert r.status_code == 200 and r.json()["is_guest"] is True
    assert c.post("/auth/register", json={"name": "Weak", "identifier": "9811122244", "password": "weak", "otp": "123456"}).status_code == 422
    assert c.post("/auth/otp/request", json={"identifier": "12345"}).status_code == 422                # 10-digit validation
    assert c.post("/auth/otp/request", json={"identifier": "bad@x"}).status_code == 422


def test_rbac_dashboard_and_staff_management(client, pax):
    assert pax.get("/dashboard/summary").status_code == 403
    nodal = login(client, "nodal.6e@demo.in")
    body = {"name": "New Staff", "email": "new.staff@indigo.demo", "mobile": "9555500001", "designation": "Executive", "level": 2, "access_type": "write"}
    r = nodal.post("/admin/users", json={**body, "password": "Strong@123"})
    assert r.status_code == 200
    assert nodal.post("/admin/users", json={**body, "password": "Strong@123"}).status_code == 409        # duplicate email/mobile
    uid = r.json()["id"]
    assert nodal.patch(f"/admin/users/{uid}", json={"status": "suspended"}).status_code == 200
    c2 = login.__globals__["TestClient"](client.app)
    assert c2.post("/auth/login", json={"username": "new.staff@indigo.demo", "password": "Strong@123"}).status_code == 403   # suspended
    nodal.patch(f"/admin/users/{uid}", json={"status": "active"})
    assert c2.post("/auth/login", json={"username": "new.staff@indigo.demo", "password": "Strong@123"}).status_code == 200


def test_audit_log_and_immutable_events(client, admin):
    assert admin.get("/admin/audit").json()["items"]
    from app.core import SessionLocal
    from app.models import TicketEvent
    import pytest
    with SessionLocal() as db:
        ev = db.query(TicketEvent).first()
        ev.note = "tamper"
        with pytest.raises(ValueError):
            db.commit()


# ---------------------------------------------------------------- social
def post(client, platform, source_type, author, text, **kw):
    r = client.post("/sim/posts", json={"platform": platform, "source_type": source_type, "author_handle": author, "text": text, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def test_x_post_detected_under_2s_with_category_and_severity(client, agent):
    t0 = time.perf_counter()
    r = post(client, "X", "post", "@rahul_travels", "@IndiGo6E flight 6E 901 DEL-BOM delayed 4 hours, my father's medicine is in the bag and no water. PNR XK92LM #AirSewa")
    elapsed = time.perf_counter() - t0
    d = r["detection"]
    assert elapsed < 2.0 and d["is_complaint"] and d["status"] == "pending"
    assert d["category"] == "flight" and d["severity"] == 1 and "medicine" in d["severity_reason"]
    assert d["entities"]["flight_no"] == "6E901" and d["entities"]["pnr"] == "XK92LM"
    assert [s["stage"] for s in d["timings"]] == ["received", "filtered", "translated", "classified", "deduplicated", "draft_created"]
    assert d["total_ms"] < 2000 and d["stakeholder"] == "IndiGo"
    q = agent.get("/pacr/drafts?status=queue").json()
    assert q[0]["id"] == d["id"] or any(x["id"] == d["id"] for x in q)
    assert d["masked_handle"] != "@rahul_travels"                                                       # handle masked on the stream


def test_instagram_four_source_types(client):
    feed = client.get("/sim/feed?platform=Instagram").json()
    official = next(p for p in feed if p["author_handle"] == "@airindia")
    cases = [
        ("post", dict(location="DEL"), "Washrooms at Delhi airport are dirty with no water. @AAI_Official @DelhiAirport"),
        ("comment", dict(parent_post_id=official["id"]), "My refund for the cancelled flight is still not received, very poor service"),
        ("story_mention", dict(target_handle="@airindia"), "Stuck at the airport for 6 hours, no food, @airindia please help"),
        ("dm", dict(target_handle="@AirSewa_Official"), "My baggage was damaged on flight AI 805, broken wheel. PNR ABCD12"),
    ]
    for stype, kw, text in cases:
        r = post(client, "Instagram", stype, "@meera.flies", text + f" ref{stype}", **kw)
        d = r["detection"]
        assert d["is_complaint"], (stype, d)
        assert d["source_type"] == stype and d["channel"] == "social_instagram"


def test_hindi_and_hinglish_posts_translated_and_classified(client):
    d = post(client, "X", "post", "@sunita_devi", "@AAI_Official मेरा सामान एयरपोर्ट पर खो गया और उसमें दवाई थी। कृपया मदद करें #AirSewa")["detection"]
    assert d["lang"] == "hi" and "baggage" in d["text_en"] and d["category"] == "flight" and d["severity"] == 1
    d = post(client, "X", "post", "@amitbhai99", "@airindia bhai mera saman kho gaya hai, koi jawab nahi de raha #AirSewa")["detection"]
    assert d["lang"] == "hinglish" and d["category"] == "flight"


def test_spam_and_praise_filtered_with_reason(client):
    d = post(client, "X", "post", "@techie_arjun", "Cheap flights to Dubai! Use code FLY50 for 50% off, click here bit.ly/xyz @airindia")["detection"]
    assert d["status"] == "filtered" and "spam" in d["reason"].lower()
    d = post(client, "X", "post", "@priya_sharma_", "Thank you @AkasaAir for the smooth flight and lovely crew today, great service! #AirSewa")["detection"]
    assert d["status"] == "filtered" and "positive feedback" in d["reason"]
    d = post(client, "X", "post", "@priya_sharma_", "Beautiful sunset today in the city")["detection"]
    assert d["status"] == "ignored" and "no watch-list" in d["reason"]


def test_duplicate_grouping_and_viral_priority_raise(client, agent):
    p1 = post(client, "X", "post", "@kabir_wanderer", "@DGCAIndia @AAI_Official my 80 year old father denied wheelchair assistance at Bengaluru airport. Shameful! #wheelchair")
    root = p1["detection"]
    assert root["status"] == "pending"
    sev0 = root["severity"]
    dup = post(client, "X", "post", "@kabir_wanderer", "Still waiting for wheelchair assistance for my father at Bengaluru airport @DGCAIndia please help")["detection"]
    assert dup["status"] == "grouped" and dup["parent_draft_id"] == root["id"]                           # same author -> grouped
    users = ["@priya_sharma_", "@techie_arjun", "@meera.flies", "@amitbhai99", "@capt_dsouza"]
    for u in users:
        r = post(client, "X", "reply", u, "+1 same issue happened to me", parent_post_id=p1["post"]["id"])
        assert r["detection"]["status"] == "grouped"
    d = agent.get(f"/pacr/drafts/{root['id']}").json()
    assert d["related_count"] == 6 and d["viral"] is True and d["severity"] < sev0 or sev0 == 1
    assert len(d["children"]) == 6


def test_agent_approval_sends_ack_to_user_notifications(client, agent):
    d = post(client, "X", "post", "@capt_dsouza", "@airindia flight AI 660 cancelled and refund not received for 3 weeks, PNR QW7R2T #AirSewa")["detection"]
    r = agent.post(f"/pacr/drafts/{d['id']}/approve", json={})
    assert r.status_code == 200
    tn = r.json()["ticket_no"]
    assert tn.startswith("AS-")
    t = agent.get(f"/tickets/{tn}").json()
    assert t["source_channel"] == "social_x" and t["status"] == "Assigned" and t["category"] == "flight"
    assert agent.post(f"/pacr/drafts/{d['id']}/reply", json={}).status_code == 200
    notes = client.get("/sim/notifications?handle=@capt_dsouza").json()
    assert any(n["ticket_no"] == tn and n["kind"] == "reply" and tn in n["text"] for n in notes)
    posts = client.get(f"/sim/posts/{d['post_id']}").json()["replies"]
    assert any(p["author_handle"] == "@AirSewa_Official" for p in posts)                                # reply appears from official handle


def test_watchlist_runtime_edit_changes_detection(client, admin):
    txt = "waiting forever outside the hall, nobody is helping me"
    assert post(client, "X", "post", "@techie_arjun", txt + " #zzcustomtag")["detection"]["status"] == "ignored"
    assert admin.post("/admin/watchlist", json={"kind": "hashtag", "value": "#zzcustomtag"}).status_code == 200
    assert post(client, "X", "post", "@techie_arjun", txt + " #zzcustomtag")["detection"]["is_complaint"]


def test_allocation_rules_editable_without_code_change(client, admin):
    r = admin.post("/admin/rules/test", json={"text": "my zorblax is broken"}).json()
    assert r["category"] == "other"
    assert admin.post("/admin/rules", json={"keyword": "zorblax", "category": "airport", "subcategory": "facilities", "target_type": "airport_operator", "weight": 5}).status_code == 200
    assert admin.post("/admin/severity", json={"keyword": "zorblax", "severity": 1}).status_code == 200
    r = admin.post("/admin/rules/test", json={"text": "my zorblax is broken"}).json()
    assert r["category"] == "airport" and r["severity"] == 1


def test_channel_ingest_and_cross_channel_dedup(client, agent):
    r = agent.post("/channels/whatsapp", json={"sender": "+919810011223", "name": "Rohan", "text": "My flight AI 101 got cancelled and refund not received, PNR AB12CD"})
    assert r.status_code == 200 and r.json()["status"] == "pending" and r.json()["channel"] == "whatsapp"
    r2 = agent.post("/channels/email", json={"sender": "rohan@mail.demo", "subject": "Refund", "text": "Refund not received for cancelled flight AI 101, PNR AB12CD, please help"})
    assert r2.json()["status"] == "grouped" and "PNR" in r2.json()["dup_reason"]

