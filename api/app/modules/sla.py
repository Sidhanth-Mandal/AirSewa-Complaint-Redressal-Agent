"""SLA & escalation engine (RFP 2.5.12, FRS 3.8). All times come from the DemoClock."""
from datetime import timedelta

from .. import reference as R
from ..adapters import registry
from ..core import bus, clock
from ..models import SlaPolicy, Ticket, User
from . import grievance as G

LEVEL_NAME = {1: "L1", 2: "L2", 3: "L3", 4: "Nodal Officer"}


def thresholds(p: SlaPolicy):
    return [p.e1_hours, p.e2_hours, p.e3_hours]


def stage_for(elapsed_h: float, th: list) -> int:
    return sum(1 for x in th if elapsed_h >= x)


def target_level(start_level: int, stage: int) -> int:
    return min(4, start_level + stage)


def time_state(t: Ticket, p: SlaPolicy, now=None):
    now = now or clock.now()
    elapsed = (now - (t.sla_start or t.created_at)).total_seconds() / 3600
    th = thresholds(p)
    stage = stage_for(elapsed, th)
    nxt = th[stage] if stage < 3 else None
    return {"elapsed_h": round(elapsed, 2), "stage": stage, "next_threshold_h": nxt,
            "remaining_h": round(th[0] - elapsed, 2), "breached": elapsed >= th[0]}


def sweep(db, now=None, publish=True) -> dict:
    """Evaluate all open tickets: flag breaches, send near-breach warnings, auto-escalate L1->L2->L3->Nodal->PACR."""
    now = now or clock.now()
    pols = {p.id: p for p in db.query(SlaPolicy)}
    open_t = db.query(Ticket).filter(Ticket.status.in_(R.OPEN_STATUSES + ["Provisionally Resolved"]), Ticket.queue != "committee").all()
    esc = warn = br = 0
    for t in open_t:
        p = pols.get(t.sla_policy_id)
        if not p:
            continue
        th = thresholds(p)
        elapsed = (now - (t.sla_start or t.created_at)).total_seconds() / 3600
        if t.status == "Provisionally Resolved":
            continue  # remedy pending; handled by agent reverify
        if elapsed >= th[0] and not t.breached:
            t.breached = True
            br += 1
            G.add_event(db, t, "SLA Engine", "system", "sla_breach", f"SLA breached: TAT {th[0]:.0f}h elapsed (policy: {p.name})",
                        at=(t.sla_start or t.created_at) + timedelta(hours=th[0]) if (now - (t.sla_start or t.created_at)).days > 0 else now)
        stage = stage_for(elapsed, th)
        while t.stage < stage:
            t.stage += 1
            new_level = target_level(t.start_level or 1, t.stage)
            old = t.level
            when = (t.sla_start or t.created_at) + timedelta(hours=th[t.stage - 1])
            if when > now:
                when = now
            if new_level == old and t.stage == 3:
                t.pacr_escalated = True
                t.queue = "pacr"
                G.add_event(db, t, "SLA Engine", "system", "escalation",
                            f"Final SLA threshold ({th[2]:.0f}h) crossed: ticket handed to PACR control room for coordination", at=when)
                esc += 1
                continue
            t.level = new_level
            t.escalation_count += 1
            nu = G.assign_user(db, t.assigned_org_id, new_level)
            t.assigned_user_id = nu.id if nu else None
            frm = t.status
            t.status = "Escalated"
            t.updated_at = now
            G.add_event(db, t, "SLA Engine", "system", "escalation",
                        f"Auto-escalated {LEVEL_NAME.get(old)} -> {LEVEL_NAME.get(new_level)} after {th[t.stage - 1]:.0f}h SLA breach"
                        + (f" (assigned to {nu.name})" if nu else ""), frm, "Escalated", {"level": new_level}, at=when)
            if t.stage == 3 and new_level >= 4:
                t.pacr_escalated = True
                t.queue = "pacr"
            esc += 1
            if nu:
                registry.notifier.send(db, "inapp", "in-app", f"Escalated: {t.ticket_no}", f"{t.ticket_no} auto-escalated to {LEVEL_NAME[new_level]}", ticket_id=t.id, user_id=nu.id)
            G.on_status_changed(db, t, frm, "Escalated")
        # near-breach warning for the upcoming threshold (to L3 + nodal of the organisation, FRS 3.8 #3)
        stage = t.stage
        if stage < 3 and t.warned_stage < stage and elapsed >= th[stage] * p.warn_pct:
            t.warned_stage = stage
            warn += 1
            G.add_event(db, t, "SLA Engine", "system", "near_breach", f"Approaching SLA threshold ({th[stage]:.0f}h): {th[stage] - elapsed:.1f}h left", at=now)
            for u in db.query(User).filter(User.org_id == t.assigned_org_id, ((User.role == "nodal") | ((User.role == "redressor") & (User.level == 3))), User.status == "active"):
                registry.notifier.send(db, "inapp", "in-app", f"Near SLA breach: {t.ticket_no}",
                                       f"{t.ticket_no} (S{t.severity}) will breach in {th[stage] - elapsed:.1f}h", ticket_id=t.id, user_id=u.id)
    db.commit()
    if publish and (esc or warn or br):
        bus.publish("tickets", {"type": "sla", "escalated": esc, "warned": warn, "breached": br})
    return {"escalated": esc, "near_breach": warn, "breached": br, "now": now.isoformat() + "Z"}


def advance_clock(db, hours: float) -> dict:
    clock.offset += timedelta(hours=hours)
    G.set_cfg(db, "clock_offset_s", clock.offset.total_seconds())
    G.audit(db, "admin", "clock.advance", "demo_clock", f"+{hours}h -> {clock.now().isoformat()}")
    db.commit()
    r = sweep(db)
    return {**r, "offset_hours": clock.offset.total_seconds() / 3600}

