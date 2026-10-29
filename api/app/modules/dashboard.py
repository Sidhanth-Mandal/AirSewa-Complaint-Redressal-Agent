"""MoCA dashboard aggregations (RFP 2.5.13) + PACR productivity / penalty simulation (RFP 2.28)."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from .. import reference as R
from ..core import clock, iso
from ..models import Airport, Draft, Organisation, ProductivityLog, SocialPost, Ticket, User

RESOLVED = set(R.RESOLVED_STATUSES)
OPEN = set(R.OPEN_STATUSES)


def _filtered_q(db, f: dict):
    q = db.query(Ticket)
    if f.get("date_from"):
        q = q.filter(Ticket.created_at >= f["date_from"])
    if f.get("date_to"):
        q = q.filter(Ticket.created_at <= f["date_to"])
    if f.get("category"):
        q = q.filter(Ticket.category == f["category"])
    if f.get("severity"):
        q = q.filter(Ticket.severity == int(f["severity"]))
    if f.get("status"):
        q = q.filter(Ticket.status == f["status"])
    if f.get("channel"):
        q = q.filter(Ticket.source_channel == f["channel"])
    if f.get("lang"):
        q = q.filter(Ticket.lang == f["lang"])
    if f.get("airport"):
        q = q.join(Airport, Airport.id == Ticket.airport_id).filter(Airport.code == f["airport"])
    if f.get("org"):
        q = q.join(Organisation, Organisation.id == Ticket.assigned_org_id).filter(Organisation.code == f["org"])
    if f.get("org_id"):
        q = q.filter(Ticket.assigned_org_id == f["org_id"])
    return q


def pct(a, b):
    return round(100 * a / b, 1) if b else 0.0


def avg(xs):
    xs = list(xs)
    return round(sum(xs) / len(xs), 2) if xs else 0.0


def summary(db, f: dict) -> dict:
    now = clock.now()
    cols = (Ticket.id, Ticket.created_at, Ticket.status, Ticket.category, Ticket.subcategory, Ticket.severity, Ticket.assigned_org_id,
            Ticket.airport_id, Ticket.source_channel, Ticket.lang, Ticket.breached, Ticket.level, Ticket.escalation_count, Ticket.reopen_count,
            Ticket.resolved_at, Ticket.csat, Ticket.sentiment, Ticket.fcr, Ticket.transfer_count, Ticket.assigned_user_id, Ticket.due_at,
            Ticket.first_response_at, Ticket.queue, Ticket.resolution_code, Ticket.disputed)
    q = _filtered_q(db, f).with_entities(*cols)
    rows = [dict(zip([c.key for c in cols], r)) for r in q.all()]
    orgs = {o.id: o for o in db.query(Organisation)}
    aps = {a.id: a for a in db.query(Airport)}
    users = {u.id: u for u in db.query(User).filter(User.role.in_(["redressor", "nodal"]))}
    total = len(rows)
    resolved = [r for r in rows if r["status"] in RESOLVED]
    open_ = [r for r in rows if r["status"] in OPEN]
    tat = lambda r: (r["resolved_at"] - r["created_at"]).total_seconds() / 3600  # noqa: E731
    res_tat = [tat(r) for r in resolved if r["resolved_at"]]
    breached = [r for r in rows if r["breached"]]
    reopened = [r for r in rows if r["reopen_count"] > 0 or r["status"] == "Reopened"]
    escalated = [r for r in rows if r["escalation_count"] > 0]
    kpis = {
        "total": total, "resolved": len(resolved), "pending": len(open_), "reopened": len(reopened),
        "closed": sum(1 for r in rows if r["status"] == "Closed"), "sla_breach_pct": pct(len(breached), total), "breached": len(breached),
        "escalation_rate": pct(len(escalated), total), "reopen_rate": pct(len(reopened), len(resolved) or 1), "fcr_pct": pct(sum(1 for r in resolved if r["fcr"]), len(resolved)),
        "csat": avg(r["csat"] for r in rows if r["csat"]), "sentiment": avg(r["sentiment"] for r in rows if r["sentiment"] is not None),
        "avg_tat_h": avg(res_tat), "transfer_rate": avg(r["transfer_count"] for r in rows),
        "avg_first_response_h": avg((r["first_response_at"] - r["created_at"]).total_seconds() / 3600 for r in rows if r["first_response_at"]),
        "committee_queue": sum(1 for r in rows if r["queue"] == "committee"), "pacr_queue": sum(1 for r in rows if r["queue"] == "pacr"),
        "critical_open": sum(1 for r in open_ if r["severity"] == 1), "critical_total": sum(1 for r in rows if r["severity"] == 1),
    }
    by_cat = Counter(r["category"] for r in rows)
    by_sub = Counter(f"{r['category']}/{r['subcategory']}" for r in rows)
    # stakeholder wise
    st = defaultdict(lambda: {"total": 0, "pending": 0, "breached": 0, "tats": [], "resolved": 0})
    for r in rows:
        o = orgs.get(r["assigned_org_id"])
        k = o.name if o else "Unassigned"
        s = st[k]
        s["total"] += 1
        s["pending"] += r["status"] in OPEN
        s["breached"] += bool(r["breached"])
        if r["status"] in RESOLVED:
            s["resolved"] += 1
            if r["resolved_at"]:
                s["tats"].append(tat(r))
        s["type"] = o.type if o else None
    stakeholders = sorted(({"name": k, "type": v.get("type"), "total": v["total"], "pending": v["pending"], "resolved": v["resolved"], "breached": v["breached"],
                            "breach_pct": pct(v["breached"], v["total"]), "avg_tat_h": avg(v["tats"])} for k, v in st.items()), key=lambda x: -x["total"])
    # trends
    daily = defaultdict(lambda: [0, 0, 0])
    monthly = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        d = r["created_at"].strftime("%Y-%m-%d")
        m = r["created_at"].strftime("%Y-%m")
        daily[d][0] += 1
        monthly[m][0] += 1
        if r["status"] in RESOLVED:
            daily[d][1] += 1
            monthly[m][1] += 1
        if r["breached"]:
            daily[d][2] += 1
            monthly[m][2] += 1
    days = sorted(daily)[-45:]
    trend_daily = [{"date": d, "tickets": daily[d][0], "resolved": daily[d][1], "breached": daily[d][2],
                    "sla_attainment": pct(daily[d][0] - daily[d][2], daily[d][0])} for d in days]
    months = sorted(monthly)
    trend_monthly = []
    for i, m in enumerate(months):
        prev = monthly[months[i - 1]][0] if i else None
        trend_monthly.append({"month": m, "tickets": monthly[m][0], "resolved": monthly[m][1], "breached": monthly[m][2],
                              "growth_pct": pct(monthly[m][0] - prev, prev) if prev else 0})
    # TAT distribution + early/within/delayed
    buckets = [("<4h", 4), ("4-12h", 12), ("12-24h", 24), ("1-3d", 72), ("3-7d", 168), (">7d", 1e9)]
    tdist = [{"bucket": b, "count": 0} for b, _ in buckets]
    for h in res_tat:
        for i, (_, lim) in enumerate(buckets):
            if h < lim:
                tdist[i]["count"] += 1
                break
    early = within = late = 0
    for r in resolved:
        if not r["resolved_at"] or not r["due_at"]:
            continue
        allowed = (r["due_at"] - r["created_at"]).total_seconds() / 3600
        h = tat(r)
        if h <= allowed * 0.5:
            early += 1
        elif h <= allowed:
            within += 1
        else:
            late += 1
    # officer / agency pendency
    pend = Counter(r["assigned_user_id"] for r in open_ if r["assigned_user_id"])
    officer_pendency = [{"officer": users[u].name if u in users else str(u), "org": users[u].org.code if u in users and users[u].org else None,
                         "level": users[u].level if u in users else None, "pending": c} for u, c in pend.most_common(10)]
    agency = defaultdict(lambda: [0, []])
    for r in rows:
        o = orgs.get(r["assigned_org_id"])
        if o and o.type == "airline" and r["resolved_at"]:
            agency[o.name][1].append(tat(r))
    agency_resp = sorted(({"name": k, "avg_tat_h": avg(v[1]), "n": len(v[1])} for k, v in agency.items()), key=lambda x: x["avg_tat_h"])
    esc_levels = Counter(r["level"] for r in rows if r["escalation_count"] > 0)
    esc_res = [tat(r) for r in escalated if r["resolved_at"]]
    # Pareto
    def pareto(counter, n=10):
        tot = sum(counter.values()) or 1
        run, out = 0, []
        for k, v in counter.most_common(n):
            run += v
            out.append({"name": k, "count": v, "cum_pct": round(100 * run / tot, 1)})
        return out
    breach_by_sub = Counter(f"{r['category']}/{r['subcategory']}" for r in breached)
    # map by airport
    amap = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        a = amap[r["airport_id"]]
        a[0] += 1
        a[1] += bool(r["breached"])
        a[2] += r["status"] in OPEN
    airport_map = []
    for aid, (n, b, p) in amap.items():
        a = aps.get(aid)
        if a:
            airport_map.append({"code": a.code, "city": a.city, "state": a.state, "row": a.row, "col": a.col, "major": a.major, "tickets": n,
                                "breach_pct": pct(b, n), "pending": p})
    state_map = defaultdict(lambda: [0, 0])
    for a in airport_map:
        state_map[a["state"]][0] += a["tickets"]
        state_map[a["state"]][1] += a["breach_pct"] * a["tickets"] / 100
    states = sorted(({"state": s, "tickets": v[0], "breach_pct": pct(v[1], v[0])} for s, v in state_map.items()), key=lambda x: -x["tickets"])
    major = [r for r in rows if aps.get(r["airport_id"]) and aps[r["airport_id"]].major]
    # cohorts
    bc, cc = Counter(), Counter()
    for r in rows:
        a = aps.get(r["airport_id"])
        key = (r["category"], a.code if a else "N/A", f"S{r['severity']}")
        cc[key] += 1
        if r["breached"]:
            bc[key] += 1
    cohort = lambda c, tot: [{"category": k[0], "airport": k[1], "priority": k[2], "count": v, "share_pct": pct(v, tot)} for k, v in c.most_common(12)]  # noqa: E731
    # live queue (hourly inflow / outflow last 24h, ageing)
    hours = []
    for i in range(23, -1, -1):
        s = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=i)
        e = s + timedelta(hours=1)
        hours.append({"hour": s.strftime("%H:00"), "inflow": sum(1 for r in rows if s <= r["created_at"] < e),
                      "outflow": sum(1 for r in rows if r["resolved_at"] and s <= r["resolved_at"] < e)})
    ageing = [("<1d", 24), ("1-3d", 72), ("3-7d", 168), ("7-14d", 336), (">14d", 1e9)]
    age = [{"bucket": b, "count": 0} for b, _ in ageing]
    qtime = defaultdict(list)
    for r in open_:
        h = (now - r["created_at"]).total_seconds() / 3600
        qtime[f"S{r['severity']}"].append(h)
        for i, (_, lim) in enumerate(ageing):
            if h < lim:
                age[i]["count"] += 1
                break
    inactive = sum(1 for r in rows if r["status"] in ("Closed",))
    active = len(open_) + sum(1 for r in rows if r["status"] in ("Provisionally Resolved", "Resolved"))
    # weekly sentiment vs csat
    wk = defaultdict(lambda: [[], []])
    for r in rows:
        k = (r["created_at"] - timedelta(days=r["created_at"].weekday())).strftime("%Y-%m-%d")
        if r["sentiment"] is not None:
            wk[k][0].append(r["sentiment"])
        if r["csat"]:
            wk[k][1].append(r["csat"])
    sentiment_trend = [{"week": k, "sentiment": avg(v[0]), "csat": avg(v[1])} for k, v in sorted(wk.items())][-26:]
    chan = Counter(r["source_channel"] for r in rows)
    chan_month = defaultdict(Counter)
    for r in rows:
        chan_month[r["created_at"].strftime("%Y-%m")][r["source_channel"]] += 1
    langs = defaultdict(lambda: [0, []])
    for r in rows:
        langs[r["lang"] or "en"][0] += 1
        if r["resolved_at"]:
            langs[r["lang"] or "en"][1].append(tat(r))
    # chronic watchlist: stakeholders with breach% high and volume
    watch = [s for s in stakeholders if s["total"] >= 20 and s["breach_pct"] >= 25][:6]
    sev_mix = Counter(f"S{r['severity']}" for r in rows)
    status_mix = Counter(r["status"] for r in rows)
    reopen_reasons = Counter(r["subcategory"] for r in reopened)
    # simple anomaly alerts: last-24h volume spike by category vs 30d baseline
    alerts = []
    last24 = Counter(r["category"] for r in rows if r["created_at"] >= now - timedelta(hours=24))
    base = Counter(r["category"] for r in rows if now - timedelta(days=31) <= r["created_at"] < now - timedelta(hours=24))
    for c, n in last24.items():
        b = base.get(c, 0) / 30
        if n >= 5 and n > 2 * max(b, 1):
            alerts.append({"type": "spike", "text": f"Spike in {c} complaints: {n} in last 24h vs ~{b:.0f}/day baseline"})
    if kpis["sla_breach_pct"] > 30:
        alerts.append({"type": "breach", "text": f"SLA breach rate {kpis['sla_breach_pct']}% exceeds 30% threshold"})
    return {
        "generated_at": iso(now), "kpis": kpis, "by_category": [{"name": k, "count": v} for k, v in by_cat.most_common()],
        "by_subcategory": [{"name": k, "count": v} for k, v in by_sub.most_common(15)], "stakeholders": stakeholders[:20],
        "trend_daily": trend_daily, "trend_monthly": trend_monthly, "tat_distribution": tdist,
        "resolution_timing": [{"name": "Resolved early", "count": early}, {"name": "Within TAT", "count": within}, {"name": "Delayed", "count": late}],
        "officer_pendency": officer_pendency, "agency_response": agency_resp,
        "escalations": {"by_level": [{"level": f"L{k}" if k < 4 else "Nodal", "count": v} for k, v in sorted(esc_levels.items())],
                        "avg_resolution_h": avg(esc_res), "total": len(escalated)},
        "pareto_volume": pareto(by_sub), "pareto_breach": pareto(breach_by_sub), "airport_map": airport_map, "state_map": states,
        "major_vs_small": {"major": len(major), "smaller": total - len(major)},
        "breach_cohorts": cohort(bc, len(breached) or 1), "complaint_cohorts": cohort(cc, total or 1),
        "live_queue": {"hourly": hours, "ageing": age, "active": active, "inactive": inactive,
                       "queue_time_by_severity": [{"severity": k, "avg_age_h": avg(v)} for k, v in sorted(qtime.items())]},
        "sentiment_trend": sentiment_trend, "channel_mix": [{"name": k, "count": v} for k, v in chan.most_common()],
        "channel_trend": [{"month": m, **dict(c)} for m, c in sorted(chan_month.items())],
        "language": [{"lang": k, "count": v[0], "avg_tat_h": avg(v[1])} for k, v in langs.items()], "watchlist": watch,
        "severity_mix": [{"name": k, "count": v} for k, v in sorted(sev_mix.items())], "status_mix": [{"name": k, "count": v} for k, v in status_mix.most_common()],
        "reopen_reasons": [{"name": k, "count": v} for k, v in reopen_reasons.most_common(8)], "alerts": alerts,
    }


def forecast(db, weeks=8):
    """Moving-average + seasonal-index forecast of ticket volume and breach-risk (simple, explainable)."""
    now = clock.now()
    rows = db.query(Ticket.created_at, Ticket.category, Ticket.breached).filter(Ticket.created_at >= now - timedelta(days=370)).all()
    wk = Counter()
    wkb = Counter()
    for c, cat, b in rows:
        k = (c - timedelta(days=c.weekday())).strftime("%Y-%m-%d")
        wk[k] += 1
        wkb[k] += bool(b)
    keys = sorted(wk)[:-1][-52:]
    vals = [wk[k] for k in keys]
    month_avg = defaultdict(list)
    for k in keys:
        month_avg[int(k[5:7])].append(wk[k])
    overall = sum(vals) / len(vals) if vals else 0
    ma = sum(vals[-4:]) / max(1, len(vals[-4:]))
    out = []
    start = now - timedelta(days=now.weekday())
    for i in range(1, weeks + 1):
        d = start + timedelta(weeks=i)
        si = (sum(month_avg[d.month]) / len(month_avg[d.month]) / overall) if month_avg.get(d.month) and overall else 1.0
        out.append({"week": d.strftime("%Y-%m-%d"), "forecast": round(ma * si), "seasonal_index": round(si, 2)})
    risk = []
    cat_b = defaultdict(lambda: [0, 0])
    for _c, cat, b in rows:
        cat_b[cat][0] += 1
        cat_b[cat][1] += bool(b)
    for cat, (n, b) in cat_b.items():
        risk.append({"category": cat, "breach_rate_pct": pct(b, n), "risk": "High" if pct(b, n) > 30 else "Medium" if pct(b, n) > 18 else "Low"})
    history = [{"week": k, "tickets": wk[k], "breached": wkb[k]} for k in sorted(wk)[-20:-1]]
    return {"history": history, "forecast": out, "breach_risk": sorted(risk, key=lambda x: -x["breach_rate_pct"]), "method": "4-week moving average x monthly seasonal index"}


# ---------------------------------------------------------------- PACR productivity (RFP 2.28)
def pu_of(inbound=0, outbound=0, email=0, chat=0) -> float:
    return inbound * 1 + outbound * 1 + email * 0.5 + chat * 0.75


def pu_penalty(pu: float, target: float = 60) -> int:
    short = max(0.0, target - pu)
    if short <= 7:
        return 0
    if short <= 20:
        return 500
    if short <= 40:
        return 1000
    return 1500


def productivity(db, days=30, target=60, invoice=5_000_000, agents_override=None) -> dict:
    now = clock.now()
    since = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    logs = db.query(ProductivityLog).filter(ProductivityLog.day >= since).all()
    users = {u.id: u for u in db.query(User).filter(User.role == "agent")}
    per_agent = defaultdict(lambda: {"shifts": 0, "pu": 0.0, "penalty": 0, "short_shifts": 0})
    rows = []
    for l in logs:
        pu = pu_of(l.inbound or 0, l.outbound or 0, l.email or 0, l.chat or 0)
        pen = pu_penalty(pu, target)
        a = per_agent[l.agent_id]
        a["shifts"] += 1
        a["pu"] += pu
        a["penalty"] += pen
        a["short_shifts"] += pen > 0
        rows.append({"agent": users[l.agent_id].name if l.agent_id in users else l.agent_id, "day": l.day, "shift": l.shift, "inbound": l.inbound,
                     "outbound": l.outbound, "email": l.email, "chat": l.chat, "pu": pu, "penalty": pen})
    agents = [{"agent": users[k].name if k in users else k, "shifts": v["shifts"], "avg_pu": round(v["pu"] / v["shifts"], 1) if v["shifts"] else 0,
               "short_shifts": v["short_shifts"], "penalty": v["penalty"]} for k, v in per_agent.items()]
    gross = sum(a["penalty"] for a in agents)
    cap = invoice * 0.10
    today = now.strftime("%Y-%m-%d")
    return {"target": target, "agents": sorted(agents, key=lambda a: a["avg_pu"]), "gross_penalty": gross, "cap": cap, "payable_penalty": min(gross, cap),
            "capped": gross > cap, "recent": sorted(rows, key=lambda r: (r["day"], r["shift"]), reverse=True)[:40],
            "today": [r for r in rows if r["day"] == today], "invoice": invoice,
            "weights": {"inbound": 1, "outbound": 1, "email/ticket/social": 0.5, "chat": 0.75},
            "slabs": [{"shortfall": "up to 7 PU", "penalty": 0}, {"shortfall": "8-20 PU", "penalty": 500}, {"shortfall": "21-40 PU", "penalty": 1000}, {"shortfall": "> 40 PU", "penalty": 1500}]}


def social_pulse(db, days=30) -> dict:
    now = clock.real_now()
    since = now - timedelta(days=days)
    ds = db.query(Draft).filter(Draft.created_at >= since, Draft.is_complaint == True, Draft.channel.in_(["social_x", "social_instagram"])).all()  # noqa: E712
    by_platform = Counter((d.channel, d.source_type) for d in ds)
    airlines = Counter(d.stakeholder for d in ds if d.category == "flight" and d.stakeholder)
    airports = Counter()
    aps = {a.id: a.code for a in db.query(Airport)}
    for d in ds:
        if d.airport_id in aps:
            airports[aps[d.airport_id]] += 1
    tags = Counter()
    for p in db.query(SocialPost).filter(SocialPost.created_at >= since):
        for h in p.hashtags or []:
            tags[h] += 1
    sent = defaultdict(list)
    for d in ds:
        sent[d.created_at.strftime("%Y-%m-%d")].append(d.sentiment or 0)
    return {"total": len(ds), "filtered": db.query(Draft).filter(Draft.created_at >= since, Draft.is_complaint == False).count(),  # noqa: E712
            "by_platform": [{"platform": "X" if c == "social_x" else "Instagram", "source_type": s, "count": n} for (c, s), n in by_platform.most_common()],
            "top_airlines": [{"name": k, "count": v} for k, v in airlines.most_common(6)], "top_airports": [{"name": k, "count": v} for k, v in airports.most_common(6)],
            "sentiment_trend": [{"date": k, "sentiment": avg(v)} for k, v in sorted(sent.items())][-30:],
            "hashtags": [{"tag": k, "count": v} for k, v in tags.most_common(8)], "viral": sum(1 for d in ds if d.viral)}
