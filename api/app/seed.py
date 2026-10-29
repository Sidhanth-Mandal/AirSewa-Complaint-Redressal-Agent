"""Seed script: reference data, demo accounts, ~3,000 tickets over 12 months, ~300 simulated social posts, story tickets, PACR productivity."""
import math
import random
import string
import sys
from collections import defaultdict
from datetime import timedelta

from . import reference as R
from .adapters import registry
from .core import Base, DB_PATH, SessionLocal, clock, engine, hash_password
from .models import (Airport, AllocationRule, CarRule, Config, Draft, Organisation, ProductivityLog, SeverityKeyword, SlaPolicy, SocialNotification,
                     SocialPost, SocialUser, Ticket, TicketEvent, User, WatchItem)
from .modules import allocation, closure, sla
from .modules import grievance as G
from .modules import social as S
from .routers.social_api import PostIn, make_post, post_ctx
from .seed_data import *  # noqa

DEMO_PW = "Demo@1234"
rnd = random.Random(2026)
N_TICKETS = 3000

AIRLINE_W = {"6E": 40, "AI": 20, "QP": 8, "SG": 6, "IX": 13, "S5": 2, "9I": 4, "I5": 2}
BREACH_P = {"6E": 0.17, "AI": 0.34, "QP": 0.12, "SG": 0.42, "IX": 0.30, "S5": 0.2, "9I": 0.38, "I5": 0.25, "DIAL": 0.15, "MIAL": 0.18, "BIAL": 0.14,
            "GHIAL": 0.14, "CIAL": 0.12, "AAI": 0.27, "SATS": 0.30, "CELEBI": 0.22, "BIRD": 0.35, "CISF": 0.25, "CUSTOMS": 0.40, "IMMIG": 0.33,
            "DGCA": 0.2, "BCAS": 0.2, "MMT": 0.2, "CLEAR": 0.2}
AIRPORT_W = {"DEL": 22, "BOM": 18, "BLR": 14, "HYD": 9, "MAA": 7, "CCU": 6, "AMD": 4, "PNQ": 3, "GOI": 3, "COK": 3, "TRV": 1.5, "JAI": 2.5, "LKO": 2.5,
             "GAU": 1.5, "PAT": 1.2, "IXC": 1.2, "BBI": 1.2, "IDR": 1, "SXR": 0.8, "VNS": 0.8}
MONTH_MULT = {1: 1.35, 2: 1.0, 3: 0.95, 4: 1.0, 5: 1.15, 6: 1.1, 7: 1.25, 8: 1.2, 9: 0.9, 10: 1.1, 11: 1.0, 12: 1.45}
CHANNEL_W = [("portal", 28), ("social_x", 48), ("social_instagram", 3.5), ("whatsapp", 5), ("email", 6), ("ivr", 3.5), ("cpgrams", 4), ("letter", 2)]


def wchoice(d):
    items = list(d.items()) if isinstance(d, dict) else d
    return rnd.choices([k for k, _ in items], weights=[w for _, w in items])[0]


def pnr():
    return "".join(rnd.choice(string.ascii_uppercase + string.digits) for _ in range(5)) + rnd.choice(string.digits)


def reset_db():
    if DB_PATH.startswith("sqlite"):
        engine.dispose()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def seed_reference(db):
    for code, name, typ, handle, crm in R.ORGS:
        db.add(Organisation(code=code, name=name, type=typ, handle=handle, has_crm=crm))
    db.flush()
    orgs = {o.code: o for o in db.query(Organisation)}
    for code, name, city, state, op, major, handle, row, col in R.AIRPORTS:
        db.add(Airport(code=code, name=name, city=city, state=state, operator_id=orgs[op].id, major=major, handle=handle, row=row, col=col))
    for kw, cat, sub, tt, oc, w in R.ALLOCATION_RULES:
        db.add(AllocationRule(keyword=kw, category=cat, subcategory=sub, target_type=tt, target_org_code=oc, weight=w))
    for kw, sv in R.SEVERITY_KEYWORDS:
        db.add(SeverityKeyword(keyword=kw, severity=sv))
    for n, c, s, e1, e2, e3 in R.SLA_POLICIES:
        db.add(SlaPolicy(name=n, category=c, severity=s, e1_hours=e1, e2_hours=e2, e3_hours=e3))
    for code, title, sub, rt, params in R.CAR_RULES:
        db.add(CarRule(code=code, title=title, subcategory=sub, rule_type=rt, params=params))
    for k, v in R.CONFIG_DEFAULTS.items():
        db.add(Config(key=k, value=v))
    db.add(Config(key="clock_offset_s", value=0))
    for h, label in R.WATCH_DEFAULT_HANDLES:
        db.add(WatchItem(kind="handle", value=h, label=label))
    for h in R.WATCH_DEFAULT_HASHTAGS:
        db.add(WatchItem(kind="hashtag", value=h, label="Campaign / topic"))
    db.add(WatchItem(kind="keyword", value="airsewa", label="Brand keyword"))
    db.commit()
    allocation.invalidate()


def seed_users(db):
    pw = hash_password(DEMO_PW)
    now = clock.now()
    orgs = {o.code: o for o in db.query(Organisation)}
    mob = [9100000000]

    def mk(name, email, role, org=None, level=1, desig=None, mobile=None):
        mob[0] += 1
        u = User(name=name, email=email, mobile=mobile or str(mob[0]), password_hash=pw, role=role, org_id=orgs[org].id if org else None, level=level,
                 designation=desig, status="active", created_at=now - timedelta(days=400), lang="en", user_type="Redressor" if org else "Staff",
                 backup_email="backup." + email, backup_mobile=str(mob[0] + 5000))
        db.add(u)
        return u
    mk("Admin MoCA-AAI", "admin@moca.demo", "admin", "MOCA", desig="Dashboard & Master Administrator")
    for i in range(1, 7):
        mk(["Neha Kapoor", "Ravi Menon", "Sana Qureshi", "Vikram Joshi", "Pooja Nair", "Imran Sheikh"][i - 1], f"agent{i}@pacr.demo", "agent", "PACR", desig="AirSewa Agent (PACR)")
    mk("Control Room Manager", "manager@pacr.demo", "manager", "PACR", desig="PACR Shift Manager")
    first = ["Anil", "Sunita", "Rohit", "Kavita", "Deepak", "Meena", "Arvind", "Lata", "Sanjay", "Divya", "Manoj", "Rekha", "Harish", "Anita", "Naveen"]
    last = ["Sharma", "Iyer", "Singh", "Das", "Reddy", "Khan", "Patel", "Gupta", "Nair", "Bose", "Verma", "Rao"]
    for code, o in orgs.items():
        if code in ("MOCA", "PACR"):
            continue
        c = code.lower()
        mk(f"{rnd.choice(first)} {rnd.choice(last)} (Nodal, {code})", f"nodal.{c}@demo.in", "nodal", code, 3, "Nodal Officer")
        for lvl, cnt in ((1, 2), (2, 1), (3, 1)):
            for k in range(cnt):
                suffix = "" if cnt == 1 else chr(97 + k)
                mk(f"{rnd.choice(first)} {rnd.choice(last)} (L{lvl}, {code})", f"{c}.l{lvl}{suffix}@demo.in", "redressor", code, lvl, f"Redressor Staff L{lvl}")
    # passengers
    p = User(name="Aarav Mehta", email="passenger@demo.in", mobile="9000000001", password_hash=pw, role="passenger", user_type="Passenger", created_at=now - timedelta(days=300), is_guest=False)
    db.add(p)
    for i in range(2, 41):
        db.add(User(name=f"{rnd.choice(first)} {rnd.choice(last)}", email=f"pax{i}@mail.demo", mobile=str(9000000000 + i), password_hash=pw, role="passenger",
                    created_at=now - timedelta(days=rnd.randint(10, 380)), is_guest=False))
    db.commit()


def seed_social_users(db):
    fake = [("@rahul_travels", "Rahul Verma", "#1d4ed8", "en", "Frequent flyer | Mumbai"), ("@priya_sharma_", "Priya Sharma", "#be185d", "en", "Travel & food | Delhi"),
            ("@amitbhai99", "Amit Patel", "#047857", "hinglish", "Hinglish tweets | Ahmedabad"), ("@sunita_devi", "सुनीता देवी", "#b45309", "hi", "हिंदी में बात | Lucknow"),
            ("@techie_arjun", "Arjun Nair", "#6d28d9", "en", "Techie | Bengaluru"), ("@meera.flies", "Meera Iyer", "#0e7490", "en", "wanderlust | Chennai"),
            ("@kabir_wanderer", "Kabir Singh", "#b91c1c", "en", "Travel blogger | Jaipur"), ("@capt_dsouza", "Joseph D'Souza", "#374151", "en", "Retired pilot | Goa")]
    for h, n, c, l, b in fake:
        db.add(SocialUser(handle=h, name=n, color=c, lang=l, bio=b, followers=rnd.randint(80, 4000)))
    offs = [("@AirSewa_Official", "AirSewa (Official)", "PACR"), ("@MoCA_GoI", "Ministry of Civil Aviation", "MOCA"), ("@AAI_Official", "Airports Authority of India", "AAI"),
            ("@DGCAIndia", "DGCA India", "DGCA"), ("@BCAS_India", "BCAS India", "BCAS"), ("@CivilAviationMinister", "Minister, Civil Aviation (placeholder)", None),
            ("@IndiGo6E", "IndiGo", "6E"), ("@airindia", "Air India", "AI"), ("@AkasaAir", "Akasa Air", "QP"), ("@flyspicejet", "SpiceJet", "SG"),
            ("@AirIndiaX", "Air India Express", "IX"), ("@DelhiAirport", "Delhi Airport", "DIAL"), ("@CSMIA_Official", "Mumbai Airport", "MIAL"),
            ("@BLRAirport", "Bengaluru Airport", "BIAL"), ("@RGIAHyderabad", "Hyderabad Airport", "GHIAL"), ("@KochiAirport", "Kochi Airport", "CIAL"), ("@CISFHQrs", "CISF", "CISF")]
    for h, n, oc in offs:
        db.add(SocialUser(handle=h, name=n, color="#0b3d91", lang="en", bio="Official account (simulated)", is_official=True, org_code=oc, followers=rnd.randint(50000, 900000)))
    db.commit()


# ------------------------------------------------------------------------------------ bulk tickets
def seed_tickets(db):
    now = clock.now()
    orgs = {o.code: o for o in db.query(Organisation)}
    orgs_by_id = {o.id: o for o in orgs.values()}
    aps = {a.code: a for a in db.query(Airport)}
    pols = db.query(SlaPolicy).all()
    rs = allocation.load_ruleset(db)
    staff = defaultdict(lambda: defaultdict(list))
    for u in db.query(User).filter(User.role.in_(["redressor", "nodal"])):
        staff[u.org_id][u.level if u.role == "redressor" else 4].append(u.id)
    pax = [u.id for u in db.query(User).filter(User.role == "passenger")]
    aw = [(c, w) for c, w in AIRPORT_W.items()]
    gsps = [orgs[c] for c in ("SATS", "CELEBI", "BIRD")]
    sub_items = [(s, v[1]) for s, v in TEMPLATES.items()]
    month_w = []
    d0 = (now - timedelta(days=365)).replace(hour=0, minute=0, second=0, microsecond=0)
    days = [d0 + timedelta(days=i) for i in range(365)]
    weights = [MONTH_MULT[d.month] * (1.15 if d.weekday() in (4, 6) else 1.0) * (0.7 + 0.5 * (i / 365)) for i, d in enumerate(days)]
    created = []
    for _ in range(N_TICKETS):
        d = rnd.choices(days, weights=weights)[0]
        t = d + timedelta(seconds=rnd.randint(0, 86399))
        created.append(min(t, now - timedelta(minutes=rnd.randint(5, 600))))
    created.sort()
    year_ctr = defaultdict(int)
    rows, evrows = [], []

    def pick_pol(cat, sev):
        best, sc = None, -1
        for p in pols:
            if (p.category and p.category != cat) or (p.severity and p.severity != sev):
                continue
            s = (2 if p.severity else 0) + (1 if p.category else 0)
            if s > sc:
                best, sc = p, s
        return best
    for i, ct in enumerate(created):
        tid = i + 1
        sub = wchoice(sub_items)
        cat, _w, tpls = TEMPLATES[sub]
        lang, tpl = rnd.choice(tpls)
        ac = wchoice(AIRLINE_W)
        ap = aps[wchoice(aw)]
        fno = f"{ac}{rnd.randint(100, 999)}"
        pn = pnr()
        text = tpl.format(airline=orgs[ac].name, flight=fno, city=ap.city, hrs=rnd.randint(2, 9), days=rnd.randint(5, 40), pnr=pn, h=orgs[ac].handle or "", tag="")
        text_en = registry.translator.translate(text, lang)
        cls = allocation.classify(text_en, rs, forced_category=cat)
        sev = cls.severity
        channel = wchoice(CHANNEL_W)
        # route
        if cat == "flight":
            org = orgs["MMT"] if sub == "refund" and rnd.random() < 0.07 else orgs[ac]
        elif cat == "airport":
            org = orgs["CISF"] if sub == "security" else orgs_by_id[ap.operator_id]
        elif cat == "ground":
            org = gsps[sum(map(ord, ap.code)) % 3]
        elif cat == "govt":
            org = orgs["CUSTOMS"] if sub == "customs" else orgs["IMMIG"] if sub == "immigration" else orgs["AAI"]
        else:
            org = orgs["AAI"]
        pol = pick_pol(cat, sev)
        start = 2 if sev == 1 else 1
        age_h = (now - ct).total_seconds() / 3600
        open_p = 0.6 if age_h < 48 else 0.2 if age_h < 168 else 0.02 if age_h < 720 else 0.003
        is_open = rnd.random() < open_p
        breach_p = BREACH_P.get(org.code, 0.25) * (1.25 if sev <= 2 else 1.0)
        will_breach = rnd.random() < breach_p
        e1, e2, e3 = pol.e1_hours, pol.e2_hours, pol.e3_hours
        res_h = e1 * rnd.uniform(1.05, 3.5 if rnd.random() < 0.7 else 5.0) if will_breach else e1 * rnd.uniform(0.04, 0.95)
        if not is_open and res_h > age_h - 1:
            is_open = True
        year_ctr[ct.year] += 1
        stage = sum(1 for x in (e1, e2, e3) if res_h >= x) if (will_breach and not is_open) else 0
        status, resolved_at, closed_at, reopen = "Assigned", None, None, 0
        transfers = 1 if rnd.random() < 0.12 else 0
        csat = None
        if not is_open:
            resolved_at = ct + timedelta(hours=res_h)
            reopen = 1 if rnd.random() < 0.085 else 0
            if reopen and rnd.random() < 0.14:
                reopen = 2
            if age_h < 336 and rnd.random() < 0.35:
                status = "Resolved" if rnd.random() < 0.75 else "Provisionally Resolved"
            else:
                status = "Closed"
                closed_at = resolved_at + timedelta(hours=rnd.uniform(1, 72))
                if closed_at > now:
                    closed_at = now
            if rnd.random() < 0.72:
                base = 4.3 - (1.6 if will_breach else 0) - 0.9 * reopen - (0.4 if sev == 1 else 0)
                csat = int(max(1, min(5, round(rnd.gauss(base, 0.9)))))
        else:
            status = rnd.choices(["Assigned", "In-Progress", "On Hold - Awaiting Passenger Inputs"], weights=[28, 55, 17])[0]
        level = min(4, start + stage)
        user_pool = staff[org.id].get(level) or staff[org.id].get(4) or []
        assigned_user = rnd.choice(user_pool) if user_pool else None
        fr = ct + timedelta(hours=e1 * rnd.uniform(0.03, 0.4)) if (not is_open or status != "Assigned") else None
        extra = {"severity_keywords": cls.severity_keywords, "entities": cls.entities}
        if sub == "refund":
            extra["ticket_amount"] = rnd.choice([3200, 4800, 5600, 7400, 9100, 12600, 18500])
        if sub in ("baggage_lost", "baggage_damaged"):
            extra["baggage_weight_kg"] = rnd.choice([15, 20, 23, 25])
        if sub in ("denied_boarding", "delay_cancellation"):
            extra["block_time_hours"] = rnd.choice([1, 1.5, 2, 2.5, 3])
            extra["ticket_amount"] = rnd.choice([3500, 5200, 6900, 9800])
        no = f"AS-{ct.year}-{year_ctr[ct.year]:06d}"
        pax_id = rnd.choice(pax)
        rows.append(dict(
            id=tid, ticket_no=no, user_id=pax_id if channel == "portal" else None, contact_name="Seeded passenger", category=cat, subcategory=sub, description=text,
            description_en=text_en, lang=lang, airline_org_id=orgs[ac].id if cat == "flight" else None, airport_id=ap.id, flight_no=fno if cat == "flight" else None,
            pnr=pn if cat == "flight" else None, service_request_no=f"SR{rnd.randint(10**7, 10**8 - 1)}" if (cat == "flight" and channel == "portal") else None,
            event_at=ct - timedelta(hours=rnd.randint(1, 30)), severity=sev, severity_reason=cls.severity_reason, status=status, source_channel=channel,
            source_type={"social_x": "post", "social_instagram": rnd.choice(["post", "comment", "dm", "story_mention"])}.get(channel),
            assigned_org_id=org.id, assigned_user_id=assigned_user, extra_org_ids=[], team=org.name, level=level, start_level=start, stage=stage,
            pacr_escalated=(level >= 4 and stage >= 3), queue="pacr" if (level >= 4 and stage >= 3 and is_open) else "redressor", sla_policy_id=pol.id, created_at=ct,
            updated_at=closed_at or resolved_at or ct, due_at=ct + timedelta(hours=e1), sla_start=ct, first_response_at=fr, resolved_at=resolved_at, closed_at=closed_at,
            breached=bool(will_breach and not is_open), warned_stage=-1, reopen_count=reopen, escalation_count=stage, transfer_count=transfers, csat=csat,
            sentiment=cls.sentiment, confidence=cls.confidence, fcr=bool(not is_open and not will_breach and not reopen and not transfers), disputed=False,
            resolution_text="Resolved with evidence (seed)" if resolved_at else None, resolution_code=sub if resolved_at else None, related_count=0, extra=extra))
        evrows.append(dict(ticket_id=tid, at=ct, actor="Complainant", actor_role="passenger", type="created", note=f"Grievance submitted via {channel}", to_status="Under Assessment", data={}))
        evrows.append(dict(ticket_id=tid, at=ct + timedelta(seconds=2), actor="AirSewa Allocation Engine", actor_role="system", type="assigned",
                           note=f"{cls.severity_reason}. Auto-routed to {org.name} at L{start}", from_status="Under Assessment", to_status="Assigned", data={}))
        for s in range(stage):
            evrows.append(dict(ticket_id=tid, at=ct + timedelta(hours=(e1, e2, e3)[s]), actor="SLA Engine", actor_role="system", type="escalation",
                               note=f"Auto-escalated after {(e1, e2, e3)[s]:.0f}h SLA breach", from_status="In-Progress", to_status="Escalated", data={}))
        if resolved_at:
            evrows.append(dict(ticket_id=tid, at=resolved_at, actor=f"Redressor ({org.code})", actor_role="redressor", type="resolved", note="Resolved with evidence",
                               from_status="In-Progress", to_status="Resolved" if status != "Provisionally Resolved" else status, data={}))
            if reopen:
                evrows.append(dict(ticket_id=tid, at=resolved_at + timedelta(hours=3), actor="Complainant", actor_role="passenger", type="reopened", note="Reopened by passenger",
                                   from_status="Resolved", to_status="Reopened", data={}))
            if closed_at:
                evrows.append(dict(ticket_id=tid, at=closed_at, actor="Complainant", actor_role="passenger", type="closed", note="Passenger confirmed", from_status="Resolved", to_status="Closed", data={}))
    db.bulk_insert_mappings(Ticket, rows)
    db.bulk_insert_mappings(TicketEvent, evrows)
    for y, n in year_ctr.items():
        db.add(Config(key=f"seq_{y}", value=n))
    db.commit()
    print(f"  tickets: {len(rows)}, events: {len(evrows)}")


# ------------------------------------------------------------------------------------ social
def fill(tpl, ac, ap):
    return tpl.format(h=ac.handle or "", airline=ac.name, flight=f"{ac.code}{rnd.randint(100, 999)}", city=ap.city, hrs=rnd.randint(2, 8), days=rnd.randint(4, 30),
                      pnr=pnr(), tag=rnd.choice(["#AirSewa", "#flightdelay", "#AirSewa", "", "#lostbaggage", "#airportcomplaint"]))


def seed_social(db, agent):
    now = clock.real_now()
    orgs = {o.code: o for o in db.query(Organisation)}
    airlines = [orgs[c] for c in AIRLINE_W]
    aplist = db.query(Airport).all()
    users = [u for u in db.query(SocialUser).filter(SocialUser.is_official == False)]  # noqa: E712
    by_handle = {u.handle: u for u in users}
    plan = []
    for i in range(300):
        age = rnd.random() ** 1.4 * 30 * 86400
        at = now - timedelta(seconds=age + 3600)
        plat = "Instagram" if rnd.random() < 0.10 else "X"
        r = rnd.random()
        kind = "complaint" if r < 0.60 else "spam" if r < 0.68 else "praise" if r < 0.80 else "meme" if r < 0.83 else "chatter" if r < 0.92 else "query"
        plan.append((at, plat, kind))
    plan.sort()
    count = 0
    for at, plat, kind in plan:
        u = rnd.choice(users)
        ac, ap = rnd.choice(airlines), rnd.choice(aplist)
        if kind == "complaint":
            lang, tpl = rnd.choice([c for c in SOCIAL_COMPLAINTS if (c[0] == "en" or rnd.random() < 0.55)])
            if u.lang in ("hi", "hinglish") and rnd.random() < 0.7:
                lang, tpl = rnd.choice([c for c in SOCIAL_COMPLAINTS if c[0] == u.lang])
            text = fill(tpl, ac, ap)
        elif kind == "spam":
            text = rnd.choice(SOCIAL_SPAM).format(h=ac.handle)
        elif kind == "praise":
            text = fill(rnd.choice(SOCIAL_PRAISE), ac, ap)
        elif kind == "meme":
            text = rnd.choice(SOCIAL_MEME).format(h=ac.handle)
        elif kind == "query":
            text = fill(rnd.choice(SOCIAL_QUERY), ac, ap)
        else:
            text = fill(rnd.choice(SOCIAL_CHATTER), ac, ap)
        if plat == "X":
            st = "post"
            tgt = None
        else:
            st = rnd.choice(["post", "post", "comment", "story_mention", "dm"])
            tgt = rnd.choice(["@airindia", "@IndiGo6E", "@AirSewa_Official", "@AAI_Official"]) if st != "post" else None
            if st == "comment":
                text = text  # comment under an official's post
        loc = ap.code if plat == "Instagram" and st == "post" else None
        media = [{"kind": "sample", "name": rnd.choice(["boarding_pass.jpg", "damaged_bag.jpg", "dirty_washroom.jpg", "queue.jpg"]), "label": "photo"}] if rnd.random() < 0.12 else []
        parent = None
        if st == "comment":
            offp = db.query(SocialPost).filter(SocialPost.platform == "Instagram", SocialPost.author_handle == tgt, SocialPost.source_type == "post").first()
            parent = offp.id if offp else None
            if not offp:
                st, tgt = "dm", tgt
        p = make_post(db, PostIn(platform=plat, source_type=st, author_handle=u.handle, text=text[:2200 if plat == "Instagram" else 280], media=media, location=loc,
                                 parent_post_id=parent, target_handle=tgt), now=at, seeded=True)
        p.likes, p.reposts = rnd.randint(0, 40), rnd.randint(0, 6)
        d = S.run_pipeline(db, post_ctx(p), publish=False, now=at, seeded=True)
        count += 1
        if d.id and d.status == "pending" and (now - at).total_seconds() > 3 * 86400:
            roll = rnd.random()
            if roll < 0.72:
                try:
                    t = S.approve(db, d, agent, {})
                    # backdate ticket to the post time and close most of them
                    t.created_at = t.sla_start = at + timedelta(minutes=rnd.randint(2, 90))
                    t.due_at = t.created_at + timedelta(hours=24)
                    if rnd.random() < 0.7:
                        t.resolved_at = t.created_at + timedelta(hours=rnd.uniform(2, 60))
                        t.closed_at = t.resolved_at + timedelta(hours=6)
                        t.status = "Closed"
                        t.csat = rnd.randint(2, 5)
                        t.resolution_text = "Resolved (seed)"
                    d.reply_sent = rnd.random() < 0.8
                except Exception:  # noqa
                    pass
            elif roll < 0.85:
                S.reject(db, d, agent, "Insufficient details to act on")
    db.commit()
    print(f"  social posts: {count}")
    return by_handle


def story_social(db, agent):
    """Scripted social stories for the demo: duplicate tweets and a viral complaint (left PENDING in the PACR queue)."""
    now = clock.real_now()
    # duplicate tweets by same author about same flight
    dup = [("@rahul_travels", "@IndiGo6E flight 6E 741 BLR-DEL delayed 3 hours, no announcement. PNR RK4P2M #flightdelay"),
           ("@rahul_travels", "Still waiting at BLR gate for 6E 741. @IndiGo6E @MoCA_GoI please respond! #AirSewa"),
           ("@priya_sharma_", "Same issue on 6E 741 from BLR, delayed 3+ hours with no food. @IndiGo6E #flightdelay")]
    for i, (h, text) in enumerate(dup):
        at = now - timedelta(minutes=50 - i * 14)
        p = make_post(db, PostIn(platform="X", source_type="post", author_handle=h, text=text), now=at, seeded=True)
        S.run_pipeline(db, post_ctx(p), publish=False, now=at, seeded=True)
    # viral thread: a wheelchair denial complaint with many +1 replies and reposts
    at = now - timedelta(hours=5)
    root = make_post(db, PostIn(platform="X", source_type="post", author_handle="@kabir_wanderer",
                                text="@DGCAIndia @AAI_Official my 80 year old father was denied wheelchair assistance at Bengaluru airport. Left stranded for an hour. Shameful!! #wheelchair #AirSewa"),
                     now=at, seeded=True)
    rd = S.run_pipeline(db, post_ctx(root), publish=False, now=at, seeded=True)
    users = ["@priya_sharma_", "@techie_arjun", "@meera.flies", "@amitbhai99", "@capt_dsouza", "@sunita_devi", "@rahul_travels"]
    for i in range(7):
        at2 = at + timedelta(minutes=8 + i * 9)
        p = make_post(db, PostIn(platform="X", source_type="reply", author_handle=users[i], parent_post_id=root.id,
                                 text=rnd.choice(["+1 same issue happened to my mother at BLR last month", "Same here, wheelchair never arrived. @AAI_Official please act", "+1 exactly the same thing at Bengaluru airport"])),
                      now=at2, seeded=True)
        S.run_pipeline(db, post_ctx(p), publish=False, now=at2, seeded=True)
    root.reposts, root.likes = 38, 214
    S.update_virality(db, rd, publish=False)
    db.commit()
    return rd


# ------------------------------------------------------------------------------------ story tickets (via real services)
def story_tickets(db):
    pax = db.query(User).filter(User.email == "passenger@demo.in").first()
    orgs = {o.code: o for o in db.query(Organisation)}
    aps = {a.code: a for a in db.query(Airport)}
    now = clock.now()

    def mk(story, created_ago_h, f, user=pax, **kw):
        f = {"consent": True, "contact_name": pax.name, "contact_mobile": pax.mobile, "contact_email": pax.email, "allow_dup": True, **f}
        t = G.create_ticket(db, f, user=user, created_at=now - timedelta(hours=created_ago_h), notify=True)
        t.extra = {**(t.extra or {}), "story": story}
        return t
    out = {}
    out["refund"] = mk("Delayed refund", 30, dict(category="flight", description="IndiGo cancelled flight 6E 512 on my booking but the refund of my ticket has not been received for 21 days. PNR RX7K2P. Service request SR55120034.",
                                              airline_org_id=orgs["6E"].id, flight_no="6E512", pnr="RX7K2P", service_request_no="SR55120034", event_at=now - timedelta(days=21),
                                              airport_id=aps["BOM"].id, extra={"ticket_amount": 8500}))
    out["baggage"] = mk("Lost baggage with medicine (S1)", 3, dict(category="flight", description="Air India flight AI 805 from Delhi to Bengaluru: my checked baggage is lost and it contains my father's life saving medicine (insulin). Urgent help needed! PNR MD3T9Q.",
                                                           airline_org_id=orgs["AI"].id, flight_no="AI805", pnr="MD3T9Q", service_request_no="SR55120077", event_at=now - timedelta(hours=5),
                                                           airport_id=aps["BLR"].id, extra={"baggage_weight_kg": 20}))
    out["washroom"] = mk("Airport washroom complaint", 8, dict(category="airport", description="The washrooms near gate 41 at Delhi airport Terminal 3 are very dirty, there is no water and a bad smell. Please clean urgently.",
                                                           airport_id=aps["DEL"].id, event_at=now - timedelta(hours=9)))
    out["wheelchair"] = mk("Wheelchair assistance", 5, dict(category="ground", description="Wheelchair assistance was not provided for my elderly mother (78) at Bengaluru airport arrival, we waited for one hour. She is a senior citizen with a heart condition.",
                                                       airport_id=aps["BLR"].id, event_at=now - timedelta(hours=6)))
    out["sla"] = mk("SLA breach auto-escalation", 20, dict(category="flight", description="SpiceJet flight SG 8169 from Delhi to Goa was delayed by 7 hours and no compensation or meals were offered. PNR SJ5K1L. Please help.",
                                                       airline_org_id=orgs["SG"].id, flight_no="SG8169", pnr="SJ5K1L", service_request_no="SR55120101", event_at=now - timedelta(hours=22),
                                                       airport_id=aps["DEL"].id, extra={"block_time_hours": 2.5, "ticket_amount": 6400}))
    # disputed closure -> committee
    t = mk("Disputed closure (Case Closure Committee)", 100, dict(category="flight", description="Akasa Air cancelled my flight QP 1332 and refused to refund the full ticket amount. PNR QK8W3N.", airline_org_id=orgs["QP"].id,
                                                                  flight_no="QP1332", pnr="QK8W3N", service_request_no="SR55120155", event_at=now - timedelta(days=5), airport_id=aps["AMD"].id,
                                                                  extra={"ticket_amount": 6000}))
    out["dispute"] = t
    db.flush()
    nod = db.query(User).filter(User.org_id == t.assigned_org_id, User.role == "nodal").first()
    G.transition(db, t, "In-Progress", nod, "Reviewing")
    closure.resolve(db, t, nod, "Refund of Rs 6000 initiated to original payment mode.", {"amount": 6000, "txn_id": "TXN-AKASA-558120"}, True)
    closure.passenger_feedback(db, t, pax, 2, False, "I was also charged a convenience fee and a rebooking fee, I want that back too.")
    # reopen_or_dispute reopened it once; now dispute it to the committee (passenger disagrees even though AI check passed)
    closure.resolve(db, t, db.query(User).filter(User.org_id == t.assigned_org_id, User.role == "nodal").first(), "Refund of Rs 6000 processed; convenience fee is non-refundable as per fare rules.",
                    {"amount": 6000, "txn_id": "TXN-AKASA-558121"}, True)
    closure.dispute(db, t, pax, "Resolution is CAR compliant but I disagree: fees were not refunded.")
    # a few more tickets for the demo passenger to track
    mk("Resolved awaiting feedback", 60, dict(category="flight", description="Air India Express flight IX 211 baggage delayed by 6 hours at Kochi, compensation requested. PNR IX9P2Z.",
                                              airline_org_id=orgs["IX"].id, flight_no="IX211", pnr="IX9P2Z", service_request_no="SR55120188", event_at=now - timedelta(days=3), airport_id=aps["COK"].id))
    db.commit()
    # make the resolved-awaiting-feedback one resolved
    t2 = db.query(Ticket).filter(Ticket.pnr == "IX9P2Z").first()
    n2 = db.query(User).filter(User.org_id == t2.assigned_org_id, User.role == "nodal").first()
    G.transition(db, t2, "In-Progress", n2, "Working")
    closure.resolve(db, t2, n2, "Baggage delivered to the passenger's address; compensation credited.", {"amount": 7000, "txn_id": "TXN-IX-77812"}, True)
    db.commit()
    return out


def seed_productivity(db):
    agents = db.query(User).filter(User.role == "agent").all()
    now = clock.now()
    for day in range(30):
        d = (now - timedelta(days=day)).strftime("%Y-%m-%d")
        for k, a in enumerate(agents):
            if rnd.random() < 0.12:
                continue
            shift = "ABC"[(k + day // 7) % 3]
            skill = 0.68 + 0.09 * (k % 4)
            target = 60 * rnd.uniform(skill - 0.05, skill + 0.4)
            inbound = int(target * rnd.uniform(0.25, 0.45))
            outbound = int(target * rnd.uniform(0.05, 0.2))
            chat = int(target * rnd.uniform(0.05, 0.15) / 0.75)
            email = max(0, int((target - inbound - outbound - chat * 0.75) / 0.5))
            db.add(ProductivityLog(agent_id=a.id, day=d, shift=shift, inbound=inbound, outbound=outbound, email=email, chat=chat))
    db.commit()


def seed_pacr_channels(db, agent):
    """A few drafts from non-social PACR channels waiting in the agent queue (Simulated)."""
    samples = [
        ("whatsapp", "+919810011223", "Rohan Gupta", "Hi, my flight AI 101 got cancelled and I have not got my refund for 18 days. PNR AB12CD. Please help", None),
        ("email", "meera.krishnan@mail.demo", "Meera Krishnan", "Lost baggage on 6E 204", "My checked bag did not arrive at Mumbai after flight 6E 204. It has important documents. PNR XK92LM. Please trace it urgently.", "Lost baggage on 6E 204"),
        ("ivr", "+919899887766", "Caller", "caller says: wheelchair was not available for my mother at Kolkata airport, we waited one hour, she is a senior citizen", None),
        ("cpgrams", "PMOPG/E/2026/0045123", "Citizen", "The washroom at Lucknow airport is dirty and there is no drinking water. Forwarded from CPGRAMS for action.", None),
        ("letter", "Letter ref LTR/445", "S. K. Banerjee", "Respected Sir, I am a senior citizen. At Kolkata airport customs officers demanded unfair duty on my gift items. Kindly look into this malpractice.", None),
    ]
    for ch, sender, name, a, *rest in samples:
        text = rest[0] if rest and isinstance(rest[0], str) and ch == "email" else a
        subj = rest[1] if len(rest) > 1 else None
        d = S.run_pipeline(db, {"channel": ch, "source_type": ch, "text": ((subj + ". ") if subj else "") + text, "author_handle": sender, "author_name": name, "skip_relevance": True,
                                "payload": {"from": sender, "subject": subj}}, publish=False, seeded=True)
        if ch in ("letter", "ivr"):
            d.media_note = ("Text extracted by simulated OCR from scanned letter" if ch == "letter" else "Transcribed by simulated speech-to-text") + " (Simulated)"
    db.commit()


def seed_minimal(db):
    seed_reference(db)
    seed_users(db)
    seed_social_users(db)
    for h, txt in (("@airindia", "Travel tips for a smooth journey with Air India. Tell us your experience!"), ("@IndiGo6E", "Fly smart this festive season with IndiGo."),
                   ("@AirSewa_Official", "AirSewa: raise your air travel grievances with us. DM or tag @AirSewa_Official")):
        su = db.query(SocialUser).filter(SocialUser.handle == h).first()
        db.add(SocialPost(platform="Instagram", source_type="post", author_handle=h, author_name=su.name, text=txt, created_at=clock.real_now() - timedelta(days=2),
                          lang="en", mentions=[], hashtags=[], media=[{"kind": "sample", "name": "promo.jpg", "label": "official post"}], likes=rnd.randint(300, 4000), url=""))
    db.commit()


def run():
    print("Resetting database ...")
    reset_db()
    with SessionLocal() as db:
        print("Reference data, users ...")
        seed_minimal(db)
        print("Bulk tickets ...")
        seed_tickets(db)
        agent = db.query(User).filter(User.email == "agent1@pacr.demo").first()
        print("Social posts ...")
        seed_social(db, agent)
        story_social(db, agent)
        seed_pacr_channels(db, agent)
        print("Story tickets ...")
        story_tickets(db)
        seed_productivity(db)
        print("Running SLA sweep for open tickets ...")
        print("  ", sla.sweep(db, publish=False))
    print("Seed complete.")


if __name__ == "__main__":
    run()


