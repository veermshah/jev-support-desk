"""Ask Jev every triage question about a ticket in one request and turn the typed answers into actions.

Jev supplies the judgments (which queue, how severe, is the customer blocked). Code owns everything else:
thresholds, priority, date arithmetic, and what to do when the model is unsure.
"""

import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass, field

from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, Score, SystemOneResponse

from jev_support_desk.taxonomy import (
    DIAGNOSTICS_CHECKLIST,
    FRUSTRATION_LEVELS,
    KB_ARTICLES,
    KB_DESCRIPTIONS,
    QUEUES,
    SEVERITY_LEVELS,
)
from jev_support_desk.tickets import Ticket

QUESTIONS = {
    "queue": Choice(
        instructions="Which support queue should handle the customer's `message`? Pick the queue for the "
        "underlying problem, not for words that merely appear in the message.",
        criteria=QUEUES,
    ),
    "severity": Score(
        instructions="How severe is the impact on the customer right now, based on the `message`?",
        criteria=SEVERITY_LEVELS,
    ),
    "blocked": Noul(
        instructions="Is the customer currently unable to continue their work until support or engineering helps?",
        criteria={
            "true": "They cannot proceed: requests fail, they cannot log in, or they cannot ship",
            "false": "They can keep working: it is a question, a feature request, or a workaround exists",
        },
    ),
    "needs_engineering": Noul(
        instructions="Does resolving this require TypeSafe engineers to investigate a defect or incident on "
        "TypeSafe's side, rather than the customer changing their own code, key, or configuration?",
        criteria={
            "true": "Likely a platform bug, regression, outage, or malformed API response",
            "false": "Likely user error, configuration, usage question, billing, or account admin",
        },
    ),
    "missing_diagnostics": Noul(
        instructions="Would support have to reply asking the customer for more information before anyone could "
        "start investigating? Judge whether the `message` is too vague to act on, not whether every possible "
        "detail is present.",
        criteria={
            "true": "Vague report such as 'it doesn't work' or 'I get an error' with no status code, error text, "
            "or description of what was sent",
            "false": "Names a concrete error, status code, message, request, or behaviour support can act on, or "
            "is not a technical problem at all",
        },
    ),
    "frustration": Score(
        instructions="How frustrated does the customer sound in the `message`?",
        criteria=FRUSTRATION_LEVELS,
    ),
    "kb_article": Choice(
        instructions="Which single documentation article would most help answer the customer's `message`?",
        criteria=KB_DESCRIPTIONS,
    ),
}


@dataclass(frozen=True)
class Thresholds:
    """Decision thresholds. Tune them with `jev-desk eval`, not by feel."""

    route_confidence: float = 0.6
    misroute_confidence: float = 0.6
    blocked: float = 0.5
    engineering: float = 0.7
    diagnostics: float = 0.6
    kb_confidence: float = 0.4
    uncertain_band: tuple[float, float] = (0.35, 0.65)


DEFAULT_THRESHOLDS = Thresholds()


@dataclass(frozen=True)
class Triage:
    ticket_id: str
    queue: str
    queue_confidence: float
    queue_probabilities: dict[str, float]
    severity: float
    severity_confidence: float
    blocked: float
    needs_engineering: float
    missing_diagnostics: float
    frustration: float
    kb_article: str
    kb_confidence: float
    model: str
    latency_ms: float
    input_tokens: int | None


@dataclass(frozen=True)
class Decision:
    """What the desk does with a ticket, derived in code from a `Triage` and `Thresholds`."""

    route: str
    auto_routed: bool
    priority: str
    actions: tuple[str, ...]
    ask_for: tuple[str, ...]
    kb_url: str | None
    uncertain: tuple[str, ...] = field(default_factory=tuple)


def triage_from_response(ticket_id: str, response: SystemOneResponse, latency_ms: float) -> Triage:
    queue = response.choices["queue"]
    severity = response.scores["severity"]
    kb = response.choices["kb_article"]
    return Triage(
        ticket_id=ticket_id,
        queue=queue.choice,
        queue_confidence=queue.confidence,
        queue_probabilities=dict(queue.probabilities),
        severity=severity.score,
        severity_confidence=severity.confidence,
        blocked=response.nouls["blocked"].noul,
        needs_engineering=response.nouls["needs_engineering"].noul,
        missing_diagnostics=response.nouls["missing_diagnostics"].noul,
        frustration=response.scores["frustration"].score,
        kb_article=kb.choice,
        kb_confidence=kb.confidence,
        model=response.model,
        latency_ms=latency_ms,
        input_tokens=response.usage.input_tokens,
    )


def priority_for(triage: Triage, ticket: Ticket, t: Thresholds) -> str:
    blocked = triage.blocked >= t.blocked
    if (blocked and triage.severity >= 2.5) or (triage.severity >= 2.5 and ticket.customer_tier == "enterprise"):
        return "P1"
    if blocked or triage.severity >= 1.5:
        return "P2"
    return "P3"


def decide(triage: Triage, ticket: Ticket, t: Thresholds = DEFAULT_THRESHOLDS) -> Decision:
    auto = triage.queue_confidence >= t.route_confidence
    actions: list[str] = []
    ask_for: tuple[str, ...] = ()
    if not auto:
        actions.append("human_routing_review")
    if triage.needs_engineering >= t.engineering:
        actions.append("escalate_to_engineering")
    if triage.missing_diagnostics >= t.diagnostics:
        ask_for = tuple(DIAGNOSTICS_CHECKLIST.get(triage.queue, ()))
        if ask_for:
            actions.append("request_diagnostics")
    kb_url = None
    if triage.kb_article != "none" and triage.kb_confidence >= t.kb_confidence:
        kb_url = KB_ARTICLES[triage.kb_article]
        actions.append("suggest_kb_article")
    low, high = t.uncertain_band
    uncertain = tuple(
        name
        for name, p in (
            ("blocked", triage.blocked),
            ("needs_engineering", triage.needs_engineering),
            ("missing_diagnostics", triage.missing_diagnostics),
        )
        if low <= p <= high
    )
    return Decision(
        route=triage.queue if auto else "triage_review",
        auto_routed=auto,
        priority=priority_for(triage, ticket, t),
        actions=tuple(actions),
        ask_for=ask_for,
        kb_url=kb_url,
        uncertain=uncertain,
    )


def is_misrouted(triage: Triage, ticket: Ticket, t: Thresholds = DEFAULT_THRESHOLDS) -> bool:
    return (
        ticket.assigned_queue is not None
        and ticket.assigned_queue != triage.queue
        and triage.queue_confidence >= t.misroute_confidence
    )


class Triager:
    def __init__(self, client: AsyncTypeSafeClient, concurrency: int = 8) -> None:
        self._client = client
        self._semaphore = asyncio.Semaphore(concurrency)

    async def triage(self, ticket: Ticket) -> Triage:
        async with self._semaphore:
            start = time.perf_counter()
            response = await self._client.system_one(state=ticket.jev_state(), questions=QUESTIONS)
            latency_ms = (time.perf_counter() - start) * 1000
        return triage_from_response(ticket.id, response, latency_ms)

    async def triage_all(self, tickets: Sequence[Ticket]) -> list[Triage]:
        return list(await asyncio.gather(*(self.triage(ticket) for ticket in tickets)))
