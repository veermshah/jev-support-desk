from datetime import datetime, timedelta, timezone

from jev_support_desk.handoff import Row, render_handoff
from jev_support_desk.triage import decide
from tests.helpers import make_ticket, make_triage

NOW = datetime(2026, 9, 30, 21, 0, tzinfo=timezone.utc)


def _row(ticket_id: str, ticket_kwargs: dict, triage_kwargs: dict) -> Row:
    ticket = make_ticket(id=ticket_id, **ticket_kwargs)
    triage = make_triage(ticket_id=ticket_id, **triage_kwargs)
    return Row(ticket, triage, decide(triage, ticket))


def _section(report: str, title: str) -> str:
    return report.split(f"## {title}", 1)[1].split("\n## ", 1)[0]


def test_handoff_groups_and_orders_tickets() -> None:
    rows = [
        _row("T-low", {"created_at": NOW - timedelta(hours=5)}, {}),
        _row("T-down", {"created_at": NOW - timedelta(hours=1)}, {"blocked": 0.95, "severity": 2.9}),
        _row("T-late", {"promised_update_at": NOW - timedelta(minutes=90)}, {}),
        _row("T-soon", {"promised_update_at": NOW + timedelta(hours=2, minutes=5)}, {}),
        _row("T-later", {"promised_update_at": NOW + timedelta(hours=20)}, {}),
        _row("T-eng", {"status": "pending_engineering"}, {"needs_engineering": 0.9}),
        _row("T-esc", {}, {"needs_engineering": 0.9}),
        _row("T-unsure", {}, {"queue_confidence": 0.3}),
        _row("T-wrong", {"assigned_queue": "billing"}, {"queue": "auth", "queue_confidence": 0.85}),
        _row("T-done", {"status": "resolved"}, {"blocked": 0.99}),
    ]
    report = render_handoff(rows, now=NOW, shift="US → EU")

    assert report.startswith("# Shift handoff — US → EU")
    assert "9 open tickets (1 P1, 0 P2, 8 P3)" in report
    assert "T-done" not in report
    assert "T-down" in _section(report, "Blocked customers")
    due = _section(report, "Promised updates")
    assert "T-late" in due and "OVERDUE by 1h30m" in due
    assert "T-soon" in due and "due in 2h05m" in due
    assert "T-later" not in due
    assert "T-eng" in _section(report, "Waiting on engineering")
    escalate = _section(report, "Needs engineering escalation")
    assert "T-esc" in escalate and "T-eng" not in escalate
    assert "T-unsure" in _section(report, "Needs a human routing decision")
    assert "**T-wrong** assigned `billing`, Jev says `auth` (0.85)" in _section(report, "Possible misroutes")
    lines = [line for line in report.splitlines() if line.startswith("- **")]
    assert lines[0].startswith("- **T-down**")


def test_empty_sections_say_none() -> None:
    report = render_handoff([_row("T-1", {}, {})], now=NOW, shift="EU → APAC")
    assert "## Blocked customers (handle first) (0)\n- none" in report
