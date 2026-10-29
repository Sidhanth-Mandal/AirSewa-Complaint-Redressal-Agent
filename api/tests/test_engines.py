"""Unit tests: allocation engine, severity matrix, SLA/escalation maths, CAR closure rules, PACR penalty slabs, entities."""
import pytest

from app.modules import allocation as A
from app.modules import closure, dashboard, sla
from app.models import SlaPolicy

RS = A.Ruleset.default()


@pytest.mark.parametrize("text,cat,sub", [
    ("My baggage is lost after IndiGo flight 6E 204", "flight", "baggage_lost"),
    ("Refund not received for cancelled flight, PNR AB12CD", "flight", "refund"),
    ("Washrooms at Delhi airport are very dirty with no water", "airport", "hygiene"),
    ("Wheelchair assistance not provided for my mother", "ground", "wheelchair"),
    ("Customs officer demanded unfair duty on my laptop", "govt", "customs"),
    ("Flight was delayed by 5 hours, no announcement", "flight", "delay_cancellation"),
    ("Security check queue is extremely long, CISF staff rude", "airport", "security"),
    ("Suggestion: please add more benches", "other", "suggestion"),
])
def test_keyword_to_category_subcategory(text, cat, sub):
    c = A.classify(text, RS)
    assert (c.category, c.subcategory) == (cat, sub)


@pytest.mark.parametrize("text,sev,kw", [
    ("Lost baggage contains my father's medicine", 1, "medicine"),
    ("Student admit card left in baggage, exam tomorrow", 1, "admit card"),
    ("Passenger fainted, medical emergency at airport", 1, "medical emergency"),
    ("Wheelchair not given to senior citizen", 2, "wheelchair"),
    ("Flight delayed by 3 hours", 3, None),
    ("Wifi not working in the lounge", 4, "wifi"),
])
def test_severity_matrix_and_reason(text, sev, kw):
    c = A.classify(text, RS)
    assert c.severity == sev
    if kw:
        assert kw in c.severity_reason and kw in c.severity_keywords
    else:
        assert "default" in c.severity_reason


def test_s1_routes_to_l2_others_l1():
    assert A.start_level_for(1) == 2
    assert all(A.start_level_for(s) == 1 for s in (2, 3, 4))


def test_forced_category_limits_rules():
    c = A.classify("baggage was delayed and washroom dirty", RS, forced_category="airport")
    assert c.category == "airport"


def test_entity_extraction():
    e = A.extract_entities("IndiGo 6E 204 DEL-BOM delayed. PNR XK92LM on 12/10/2026 at Delhi airport")
    assert e["flight_no"] == "6E204" and e["airline_code"] == "6E"
    assert e["pnr"] == "XK92LM"
    assert e["airport_code"] == "DEL"
    assert e["date"] == "12/10/2026"


def test_entity_airline_from_handle_and_city():
    rs = A.Ruleset.default()
    e = A.extract_entities("@airindia lost my bag at Bengaluru", rs.handles)
    assert e["airline_code"] == "AI" and e["airport_code"] == "BLR"


def test_sentiment_sign():
    assert A.sentiment("Thank you, amazing and smooth flight") > 0.2
    assert A.sentiment("Worst airline, pathetic and rude staff") < -0.3


# --- SLA / escalation maths
def test_escalation_stage_and_levels():
    th = [24, 72, 96]
    assert sla.stage_for(10, th) == 0 and sla.stage_for(24, th) == 1 and sla.stage_for(80, th) == 2 and sla.stage_for(100, th) == 3
    assert [sla.target_level(1, s) for s in range(4)] == [1, 2, 3, 4]      # L1 -> L2 -> L3 -> Nodal
    assert [sla.target_level(2, s) for s in range(4)] == [2, 3, 4, 4]      # S1 starts at L2


# --- closure / CAR checks
REFUND = ("CAR-X", "Refund", "refund_min", {"percent_of_ticket": 100})


def test_refund_below_car_amount_fails():
    r = closure.car_check(REFUND, "refund", {"amount": 5000}, {"ticket_amount": 8500})
    assert r["passed"] is False and r["expected"] == 8500


def test_refund_equal_or_above_passes():
    assert closure.car_check(REFUND, "refund", {"amount": 8500}, {"ticket_amount": 8500})["passed"]
    assert closure.car_check(REFUND, "refund", {"amount": 9000}, {"ticket_amount": 8500})["passed"]


def test_compensation_table_by_block_time():
    rule = ("C", "Comp", "compensation_table", {"table": [[1, 5000], [2, 7500], [999, 10000]]})
    assert closure.car_check(rule, "x", {"amount": 7500}, {"block_time_hours": 2, "ticket_amount": 20000})["passed"]
    assert not closure.car_check(rule, "x", {"amount": 7500}, {"block_time_hours": 3, "ticket_amount": 20000})["passed"]


def test_baggage_liability_per_kg():
    rule = ("B", "Bag", "baggage_liability", {"per_kg": 350, "default_kg": 20})
    assert not closure.car_check(rule, "baggage_lost", {"amount": 5000}, {})["passed"]
    assert closure.car_check(rule, "baggage_lost", {"amount": 7000}, {})["passed"]


def test_no_rule_passes_with_evidence_only():
    assert closure.car_check(None, "hygiene", {"txn_id": "x"}, {})["passed"]


# --- PACR penalty slabs (RFP 2.28)
@pytest.mark.parametrize("pu,pen", [(60, 0), (53, 0), (52, 500), (40, 500), (39, 1000), (20, 1000), (19, 1500), (0, 1500)])
def test_pu_penalty_slabs(pu, pen):
    assert dashboard.pu_penalty(pu) == pen


def test_pu_weights():
    assert dashboard.pu_of(inbound=10, outbound=5, email=10, chat=4) == 10 + 5 + 5 + 3
