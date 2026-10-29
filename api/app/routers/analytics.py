import csv
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import reference as R
from ..core import clock, get_db, iso
from ..deps import current_user, require
from ..models import ProductivityLog, Ticket, User
from ..modules import dashboard as D
from ..modules import grievance as G

router = APIRouter(tags=["analytics"])


def _filters(date_from, date_to, airport, channel, category, severity, status, org, lang, u: User):
    f = {"airport": airport, "channel": channel, "category": category, "severity": severity, "status": status, "org": org, "lang": lang}
    f["date_from"] = datetime.fromisoformat(date_from) if date_from else None
    f["date_to"] = datetime.fromisoformat(date_to) + timedelta(days=1) if date_to else None
    if u.role == "nodal":
        f["org_id"] = u.org_id  # nodal officers see only their organisation's dashboard
    return {k: v for k, v in f.items() if v}


FILTER_PARAMS = dict(date_from=Query(None, alias="from"), date_to=Query(None, alias="to"), airport=Query(None), channel=Query(None), category=Query(None),
                     severity=Query(None), status=Query(None), org=Query(None), lang=Query(None))


@router.get("/dashboard/summary")
def dash_summary(date_from=FILTER_PARAMS["date_from"], date_to=FILTER_PARAMS["date_to"], airport=FILTER_PARAMS["airport"], channel=FILTER_PARAMS["channel"],
                 category=FILTER_PARAMS["category"], severity=FILTER_PARAMS["severity"], status=FILTER_PARAMS["status"], org=FILTER_PARAMS["org"],
                 lang=FILTER_PARAMS["lang"], u: User = Depends(require("admin", "agent", "manager", "nodal")), db: Session = Depends(get_db)):
    return D.summary(db, _filters(date_from, date_to, airport, channel, category, severity, status, org, lang, u))


@router.get("/dashboard/social-pulse")
def social_pulse(u: User = Depends(require("admin", "agent", "manager")), db: Session = Depends(get_db)):
    return D.social_pulse(db)


@router.get("/dashboard/forecast")
def forecast(u: User = Depends(require("admin", "agent", "manager")), db: Session = Depends(get_db)):
    return D.forecast(db)


@router.get("/manager/productivity")
def productivity(days: int = 30, target: float = 60, invoice: float | None = None, u: User = Depends(require("manager", "admin")), db: Session = Depends(get_db)):
    return D.productivity(db, days, target, invoice or G.cfg(db, "monthly_invoice_inr"))


@router.get("/manager/whatif")
def whatif(seats: int, u: User = Depends(require("manager", "admin")), db: Session = Depends(get_db)):
    """SIMULATED what-if staffing: expected PU shortfall/penalty vs seat count given forecast volume (illustrative model)."""
    fc = D.forecast(db)
    weekly = fc["forecast"][0]["forecast"] if fc["forecast"] else 0
    per_day_social = weekly / 7 * 1.2
    seats_cur = G.cfg(db, "pacr_seats") or 12
    shifts_per_day = 3
    pu_needed_day = per_day_social * 0.5 + 300  # assume ~300 PU/day of call/chat load (illustrative)
    pu_per_seat_shift = pu_needed_day / max(1, seats * shifts_per_day / 3)
    pen_shift = D.pu_penalty(pu_per_seat_shift)
    cost = seats * 90000
    return {"simulated": True, "seats": seats, "current_seats": seats_cur, "expected_pu_per_seat_shift": round(pu_per_seat_shift, 1),
            "penalty_per_shift": pen_shift, "monthly_penalty_estimate": pen_shift * seats * 30, "monthly_cost_estimate": cost,
            "note": "Illustrative model: 300 PU/day non-social load assumed; Rs 90,000/seat/month assumed."}


@router.get("/redressor/performance")
def performance(user_id: int | None = None, u: User = Depends(require("redressor", "nodal", "admin", "agent")), db: Session = Depends(get_db)):
    def stats(uid):
        ts = db.query(Ticket).filter(Ticket.assigned_user_id == uid).all()
        res = [t for t in ts if t.status in R.RESOLVED_STATUSES and t.resolved_at]
        return {"assigned_total": len(ts), "open": sum(1 for t in ts if t.status in R.OPEN_STATUSES), "resolved": len(res),
                "avg_tat_h": D.avg((t.resolved_at - t.created_at).total_seconds() / 3600 for t in res),
                "breached": sum(1 for t in ts if t.breached), "breach_pct": D.pct(sum(1 for t in ts if t.breached), len(ts)),
                "csat": D.avg(t.csat for t in ts if t.csat), "reopened": sum(1 for t in ts if t.reopen_count), "critical_open": sum(1 for t in ts if t.severity == 1 and t.status in R.OPEN_STATUSES)}
    if u.role == "redressor":
        return {"me": stats(u.id)}
    if u.role == "nodal":
        staff = db.query(User).filter(User.org_id == u.org_id, User.role == "redressor").all()
        rows = [{"id": s.id, "name": s.name, "level": s.level, "status": s.status, **stats(s.id)} for s in staff]
        tot = sum(r["open"] for r in rows) or 1
        return {"me": stats(u.id), "staff": rows, "fairness": [{"name": r["name"], "load_share_pct": round(100 * r["open"] / tot, 1)} for r in rows]}
    return {"me": stats(user_id or u.id)}


# ------------------------------------------------------------------ export
def _export_rows(db, f, limit=20000):
    q = D._filtered_q(db, f).order_by(Ticket.created_at.desc()).limit(limit)
    return [[t.ticket_no, iso(t.created_at), t.category, t.subcategory, f"S{t.severity}", t.status, t.source_channel, t.assigned_org.name if t.assigned_org else "",
             t.airport.code if t.airport else "", t.lang, "Y" if t.breached else "N", t.reopen_count, t.escalation_count, t.csat or ""] for t in q]


HEAD = ["Ticket", "Created", "Category", "Subcategory", "Severity", "Status", "Channel", "Stakeholder", "Airport", "Lang", "SLA breached", "Reopens", "Escalations", "CSAT"]


@router.get("/dashboard/export")
def export(fmt: str = "csv", date_from=FILTER_PARAMS["date_from"], date_to=FILTER_PARAMS["date_to"], airport=FILTER_PARAMS["airport"], channel=FILTER_PARAMS["channel"],
           category=FILTER_PARAMS["category"], severity=FILTER_PARAMS["severity"], status=FILTER_PARAMS["status"], org=FILTER_PARAMS["org"], lang=FILTER_PARAMS["lang"],
           u: User = Depends(require("admin", "agent", "manager", "nodal")), db: Session = Depends(get_db)):
    f = _filters(date_from, date_to, airport, channel, category, severity, status, org, lang, u)
    rows = _export_rows(db, f)
    G.audit(db, u.name, "export", fmt, f"{len(rows)} rows")
    db.commit()
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(HEAD)
        w.writerows(rows)
        return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=airsewa_tickets.csv"})
    s = D.summary(db, f)
    if fmt == "xlsx":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "KPIs"
        for k, v in s["kpis"].items():
            ws.append([k, v])
        w2 = wb.create_sheet("Stakeholders")
        w2.append(["Stakeholder", "Total", "Pending", "Resolved", "Breached", "Breach %", "Avg TAT (h)"])
        for x in s["stakeholders"]:
            w2.append([x["name"], x["total"], x["pending"], x["resolved"], x["breached"], x["breach_pct"], x["avg_tat_h"]])
        w3 = wb.create_sheet("Tickets")
        w3.append(HEAD)
        for r in rows:
            w3.append(r)
        out = io.BytesIO()
        wb.save(out)
        return Response(out.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": "attachment; filename=airsewa_report.xlsx"})
    if fmt == "pdf":
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        out = io.BytesIO()
        doc = SimpleDocTemplate(out, pagesize=A4, title="AirSewa MoCA Report")
        st = getSampleStyleSheet()
        els = [Paragraph("AirSewa 3.0 - MoCA/AAI Grievance Report", st["Title"]), Paragraph(f"Generated {iso(clock.now())} (prototype data)", st["Normal"]), Spacer(1, 12)]
        k = s["kpis"]
        t1 = Table([["Metric", "Value"]] + [[a, str(b)] for a, b in k.items()], hAlign="LEFT")
        t1.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b3d91")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
        els += [t1, Spacer(1, 12), Paragraph("Stakeholder-wise", st["Heading2"])]
        t2 = Table([["Stakeholder", "Total", "Pending", "Breach %", "Avg TAT h"]] + [[x["name"][:38], x["total"], x["pending"], x["breach_pct"], x["avg_tat_h"]] for x in s["stakeholders"][:20]], hAlign="LEFT")
        t2.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#138808")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
        els.append(t2)
        doc.build(els)
        return Response(out.getvalue(), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=airsewa_report.pdf"})
    raise HTTPException(422, "fmt must be csv, xlsx or pdf")
