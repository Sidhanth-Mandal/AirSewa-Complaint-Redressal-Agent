"""Closure rules (RFP 2.5.9): evidence mandatory, AI-style CAR/DGCA compliance check, passenger confirmation, reopen cap, disputes."""
from fastapi import HTTPException

from ..core import bus, clock
from ..models import CarRule, Feedback, Ticket
from . import grievance as G


def car_check(rule, subcategory: str, evidence: dict, extra: dict) -> dict:
    """Pure function: evaluate evidence against a CAR rule. `rule` = (code, title, rule_type, params) or None."""
    if not rule:
        return {"passed": True, "rule": None, "reason": "No specific CAR rule mapped; evidence present.", "expected": None}
    code, title, rtype, params = rule
    amt = float(evidence.get("amount") or 0)
    if rtype == "refund_min":
        ticket_amt = float(extra.get("ticket_amount") or 0)
        expected = round(ticket_amt * params.get("percent_of_ticket", 100) / 100, 2)
        if expected <= 0:
            return {"passed": amt > 0, "rule": code, "title": title, "reason": "Ticket amount unknown; refund amount recorded.", "expected": None}
        ok = amt + 0.001 >= expected
        return {"passed": ok, "rule": code, "title": title, "expected": expected, "provided": amt,
                "reason": f"Refund Rs {amt:,.0f} {'meets' if ok else 'is LESS than'} CAR-computed refund Rs {expected:,.0f}"}
    if rtype in ("compensation_table", "baggage_liability") and not amt:
        return {"passed": True, "rule": code, "title": title, "expected": None,
                "reason": "Non-monetary resolution (e.g. bag located / alternate flight / meals) with evidence; no compensation amount to verify."}
    if rtype == "compensation_table":
        bt = float(extra.get("block_time_hours") or 2)
        base = next(v for lim, v in params["table"] if bt <= lim)
        fare = float(extra.get("basic_fare_plus_fuel") or extra.get("ticket_amount") or 0)
        expected = min(base, fare) if fare else base
        ok = amt + 0.001 >= expected
        return {"passed": ok, "rule": code, "title": title, "expected": expected, "provided": amt,
                "reason": f"Compensation Rs {amt:,.0f} {'meets' if ok else 'is LESS than'} CAR amount Rs {expected:,.0f} (block time {bt}h)"}
    if rtype == "baggage_liability":
        kg = float(extra.get("baggage_weight_kg") or params.get("default_kg", 20))
        expected = kg * params["per_kg"]
        ok = amt + 0.001 >= expected
        return {"passed": ok, "rule": code, "title": title, "expected": expected, "provided": amt,
                "reason": f"Baggage compensation Rs {amt:,.0f} {'meets' if ok else 'is LESS than'} liability Rs {expected:,.0f} ({kg:g} kg x Rs {params['per_kg']})"}
    return {"passed": True, "rule": code, "title": title, "reason": "Evidence present.", "expected": None}


def find_rule(db, subcategory):
    r = db.query(CarRule).filter(CarRule.subcategory == subcategory, CarRule.active == True).first()  # noqa: E712
    return (r.code, r.title, r.rule_type, r.params) if r else None


def resolve(db, t: Ticket, user, resolution_text: str, evidence: dict, remedy_complete: bool, evidence_files: int = 0):
    """Stakeholder resolves a ticket. Blocked without evidence or when CAR check fails."""
    if t.status not in ("Assigned", "In-Progress", "Escalated", "Reopened", "On Hold - Awaiting Passenger Inputs"):
        raise HTTPException(409, f"Cannot resolve a ticket in status '{t.status}'")
    if user.access_type == "read" and user.role == "redressor":
        raise HTTPException(403, "Read-only account")
    if not (evidence.get("txn_id") or evidence.get("reference") or evidence_files):
        raise HTTPException(422, {"message": "Evidence is mandatory to resolve (e.g. refund transaction ID, receipt, proof upload).", "fields": ["evidence"]})
    if not resolution_text or len(resolution_text.strip()) < 5:
        raise HTTPException(422, {"message": "Resolution comments are required", "fields": ["resolution_text"]})
    res = car_check(find_rule(db, t.subcategory), t.subcategory, evidence, t.extra or {})
    t.compliance = res
    if not res["passed"]:
        G.add_event(db, t, "AI Compliance Check", "system", "compliance_fail", res["reason"], data=res)
        db.commit()
        raise HTTPException(422, {"message": "Resolution failed the CAR/DGCA compliance check: " + res["reason"], "compliance": res, "fields": ["amount"]})
    now = clock.now()
    G.add_event(db, t, "AI Compliance Check", "system", "compliance_pass", res["reason"], data=res)
    t.resolution_text = resolution_text
    t.resolution_code = t.subcategory
    t.resolved_at = now
    t.queue = "redressor"
    if not t.first_response_at:
        t.first_response_at = now
    t.fcr = (t.reopen_count == 0 and t.escalation_count == 0 and t.transfer_count == 0)
    if t.due_at and now > t.due_at:
        t.breached = True
    G.add_event(db, t, G.actor_name(user), user.role, "evidence", f"Evidence: {evidence}", data=evidence)
    G.transition(db, t, "Resolved" if remedy_complete else "Provisionally Resolved", user, resolution_text, etype="resolved")
    return res


def passenger_feedback(db, t: Ticket, user, rating: int, confirms: bool, comment: str = ""):
    if t.status not in ("Resolved", "Provisionally Resolved", "Closed"):
        raise HTTPException(409, "Feedback is possible only after the stakeholder has resolved the grievance")
    now = clock.now()
    db.add(Feedback(ticket_id=t.id, rating=rating, confirms=confirms, comment=comment, at=now))
    t.csat = rating
    G.add_event(db, t, G.actor_name(user), "passenger", "feedback", f"Rating {rating}/5; {'confirmed resolution' if confirms else 'not satisfied'}. {comment}")
    if confirms:
        t.closed_at = now
        G.transition(db, t, "Closed", user, "Passenger confirmed the resolution", etype="closed")
        return "closed"
    return reopen_or_dispute(db, t, user, comment or "Passenger not satisfied")


def reopen_or_dispute(db, t: Ticket, user, reason: str):
    maxr = G.cfg(db, "max_reopens") or 2
    if t.reopen_count >= maxr:
        return dispute(db, t, user, f"Reopen limit ({maxr}) reached. " + reason)
    t.reopen_count += 1
    t.closed_at = None
    t.resolved_at = None
    t.stage = 0
    t.breached = False
    t.warned_stage = -1
    t.level = t.start_level or 1
    from datetime import timedelta
    from ..models import SlaPolicy
    p = db.get(SlaPolicy, t.sla_policy_id) if t.sla_policy_id else None
    t.extra = {**(t.extra or {}), "reopened_at": clock.now().isoformat()}
    G.transition(db, t, "Reopened", user, f"Reopened ({t.reopen_count}/{maxr}): {reason}", etype="reopened")
    # restart the SLA clock from the reopen time (original created_at is kept for reporting)
    t.sla_start = clock.now()
    t.due_at = clock.now() + timedelta(hours=p.e1_hours) if p else None
    u = G.assign_user(db, t.assigned_org_id, t.level)
    t.assigned_user_id = u.id if u else None
    G.transition(db, t, "Assigned", user, "Re-assigned after reopen", etype="assigned")
    bus.publish("tickets", {"type": "reopened", "ticket_no": t.ticket_no})
    return "reopened"


def dispute(db, t: Ticket, user, reason: str):
    """Passenger unhappy but resolution compliant (or reopen limit reached) -> Case Closure Committee / PACR queue."""
    t.disputed = True
    t.queue = "committee"
    G.add_event(db, t, G.actor_name(user), user.role if user else "system", "disputed", reason)
    G.audit(db, G.actor_name(user), "ticket.dispute", t.ticket_no, reason)
    bus.publish("tickets", {"type": "disputed", "ticket_no": t.ticket_no})
    return "disputed"


def committee_decide(db, t: Ticket, user, decision: str, note: str):
    """decision: uphold (close as resolved) | reinstate (send back to stakeholder) | ingenuine (close as not genuine)."""
    if t.queue != "committee":
        raise HTTPException(409, "Ticket is not in the committee queue")
    now = clock.now()
    G.add_event(db, t, G.actor_name(user), user.role, "committee_decision", f"{decision}: {note}")
    t.queue = "redressor"
    t.disputed = False
    if decision in ("uphold", "ingenuine"):
        t.closed_at = now
        if t.status not in ("Resolved", "Closed", "Provisionally Resolved"):
            t.status = "Resolved"
        G.transition(db, t, "Closed", user, f"Committee decision: {decision}. {note}", etype="closed", force=True)
    else:
        t.stage = 0
        t.breached = False
        t.warned_stage = -1
        t.level = max(t.level, 2)
        G.transition(db, t, "Reopened", user, f"Reinstated by committee: {note}", etype="reopened", force=True)
        u = G.assign_user(db, t.assigned_org_id, t.level)
        t.assigned_user_id = u.id if u else None
        G.transition(db, t, "Assigned", user, "Re-assigned after committee decision", etype="assigned")
    return decision


def reverify(db, t: Ticket, user, ok: bool, note: str):
    """Agent re-verification of closure (FRS 3.5 / RFP 2.5.11 #2). Wrongful closures are reinstated."""
    G.add_event(db, t, G.actor_name(user), user.role, "reverify", f"{'Verified' if ok else 'Rejected'}: {note}")
    if not ok:
        t.closed_at = None
        t.resolved_at = None
        t.stage = 0
        t.warned_stage = -1
        t.breached = False
        G.transition(db, t, "Reopened", user, f"Wrongful closure reinstated: {note}", etype="reopened", force=True)
        u = G.assign_user(db, t.assigned_org_id, max(t.level, 2))
        t.assigned_user_id = u.id if u else None
        G.transition(db, t, "Assigned", user, "Re-assigned after reverification", etype="assigned")

