from dataclasses import replace

from jev_support_desk.tickets import Ticket
from jev_support_desk.triage import Triage

BASE = Triage(
    ticket_id="T-1",
    queue="auth",
    queue_confidence=0.9,
    queue_probabilities={"auth": 0.9, "billing": 0.1},
    severity=1.0,
    severity_confidence=0.8,
    blocked=0.1,
    needs_engineering=0.1,
    missing_diagnostics=0.1,
    frustration=1.0,
    kb_article="none",
    kb_confidence=0.9,
    model="jev-1.13.0",
    latency_ms=120.0,
    input_tokens=300,
)


def make_triage(**overrides: object) -> Triage:
    return replace(BASE, **overrides)


def make_ticket(**overrides: object) -> Ticket:
    return replace(Ticket(id="T-1", subject="401 after key rotation", body="Everything returns 401."), **overrides)
