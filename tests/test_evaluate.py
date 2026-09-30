import pytest

from jev_support_desk.evaluate import evaluate, render_report
from jev_support_desk.tickets import Labels
from tests.helpers import make_ticket, make_triage


def _labels(queue: str, blocked: bool = False) -> Labels:
    return Labels(queue=queue, severity=1, blocked=blocked, needs_engineering=False, missing_diagnostics=False)


def test_metrics_on_a_tiny_labeled_set() -> None:
    tickets = [
        make_ticket(id="A", subject="401", body="401 unauthorized", labels=_labels("auth", blocked=True)),
        make_ticket(id="B", subject="refund", body="charged twice", labels=_labels("billing")),
        make_ticket(id="C", subject="hmm", body="it broke", labels=_labels("bug_or_outage")),
        make_ticket(id="D", subject="unlabeled", body="x"),
    ]
    triages = [
        make_triage(ticket_id="A", queue="auth", queue_confidence=0.9, blocked=0.9, latency_ms=100),
        make_triage(ticket_id="B", queue="billing", queue_confidence=0.7, blocked=0.2, latency_ms=200),
        make_triage(ticket_id="C", queue="sdk_integration", queue_confidence=0.4, blocked=0.6, latency_ms=300),
        make_triage(ticket_id="D"),
    ]
    report = evaluate(tickets, triages)

    assert report.n == 3
    assert report.jev_accuracy == pytest.approx(2 / 3)
    by_threshold = {row.threshold: row for row in report.thresholds}
    assert by_threshold[0.0].coverage == 1.0
    assert by_threshold[0.6].coverage == pytest.approx(2 / 3)
    assert by_threshold[0.6].accuracy_auto == 1.0
    assert by_threshold[0.9].auto_count == 1
    blocked = next(m for m in report.nouls if m.name == "blocked")
    assert blocked.accuracy == pytest.approx(2 / 3)
    assert blocked.brier == pytest.approx((0.1**2 + 0.2**2 + 0.6**2) / 3)
    assert report.misses == [("C", "bug_or_outage", "sdk_integration", 0.4)]
    assert report.input_tokens == 900

    text = render_report(report, "jev-1.13.0")
    assert "jev-1.13.0" in text and "bug_or_outage" in text


def test_evaluate_requires_labels() -> None:
    with pytest.raises(ValueError):
        evaluate([make_ticket()], [make_triage()])
