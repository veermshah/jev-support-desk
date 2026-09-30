from jev_support_desk.taxonomy import DIAGNOSTICS_CHECKLIST
from jev_support_desk.triage import Thresholds, decide, is_misrouted
from tests.helpers import make_ticket, make_triage


def test_confident_route_is_automatic() -> None:
    d = decide(make_triage(queue_confidence=0.61), make_ticket())
    assert d.auto_routed and d.route == "auth"
    assert "human_routing_review" not in d.actions


def test_low_confidence_goes_to_human_review() -> None:
    d = decide(make_triage(queue_confidence=0.59), make_ticket())
    assert not d.auto_routed and d.route == "triage_review"
    assert "human_routing_review" in d.actions


def test_thresholds_are_configurable() -> None:
    d = decide(make_triage(queue_confidence=0.59), make_ticket(), Thresholds(route_confidence=0.5))
    assert d.auto_routed


def test_priority_rules() -> None:
    ticket = make_ticket()
    assert decide(make_triage(blocked=0.9, severity=2.8), ticket).priority == "P1"
    assert decide(make_triage(severity=2.8), make_ticket(customer_tier="enterprise")).priority == "P1"
    assert decide(make_triage(severity=2.8), ticket).priority == "P2"
    assert decide(make_triage(blocked=0.9, severity=0.5), ticket).priority == "P2"
    assert decide(make_triage(blocked=0.2, severity=1.0), ticket).priority == "P3"


def test_engineering_escalation_needs_high_probability() -> None:
    assert "escalate_to_engineering" not in decide(make_triage(needs_engineering=0.69), make_ticket()).actions
    assert "escalate_to_engineering" in decide(make_triage(needs_engineering=0.7), make_ticket()).actions


def test_missing_diagnostics_asks_for_queue_specific_details() -> None:
    d = decide(make_triage(queue="request_validation", missing_diagnostics=0.8), make_ticket())
    assert "request_diagnostics" in d.actions
    assert d.ask_for == tuple(DIAGNOSTICS_CHECKLIST["request_validation"])


def test_kb_article_only_when_confident() -> None:
    assert decide(make_triage(kb_article="retries", kb_confidence=0.3), make_ticket()).kb_url is None
    assert decide(make_triage(kb_article="retries", kb_confidence=0.5), make_ticket()).kb_url.endswith("/retries")
    assert decide(make_triage(kb_article="none", kb_confidence=0.99), make_ticket()).kb_url is None


def test_uncertain_signals_are_flagged() -> None:
    d = decide(make_triage(blocked=0.5, needs_engineering=0.9, missing_diagnostics=0.4), make_ticket())
    assert d.uncertain == ("blocked", "missing_diagnostics")


def test_misroute_requires_confident_disagreement() -> None:
    assigned = make_ticket(assigned_queue="billing")
    assert is_misrouted(make_triage(queue="auth", queue_confidence=0.8), assigned)
    assert not is_misrouted(make_triage(queue="auth", queue_confidence=0.4), assigned)
    assert not is_misrouted(make_triage(queue="billing", queue_confidence=0.9), assigned)
    assert not is_misrouted(make_triage(queue="auth", queue_confidence=0.9), make_ticket())
