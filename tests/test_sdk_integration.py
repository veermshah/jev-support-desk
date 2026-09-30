"""Exercise the real typesafe-sdk client against a mocked HTTP transport."""

import asyncio
import json

import httpx2
from typesafe_sdk import AsyncTypeSafeClient

from jev_support_desk.taxonomy import QUEUES
from jev_support_desk.triage import QUESTIONS, Triager, decide
from tests.helpers import make_ticket


def _answers(queue: str) -> dict:
    other = next(q for q in QUEUES if q != queue)
    return {
        "queue": {"type": "choice", "choice": queue, "confidence": 0.82, "probabilities": {queue: 0.85, other: 0.15}},
        "severity": {
            "type": "score",
            "score": 2.7,
            "confidence": 0.7,
            "legend": {"0": "a", "1": "b", "2": "c", "3": "d"},
            "probabilities": {"0": 0.0, "1": 0.1, "2": 0.1, "3": 0.8},
        },
        "blocked": {"type": "noul", "noul": 0.93},
        "needs_engineering": {"type": "noul", "noul": 0.12},
        "missing_diagnostics": {"type": "noul", "noul": 0.2},
        "frustration": {
            "type": "score",
            "score": 1.2,
            "confidence": 0.6,
            "legend": {"0": "a", "1": "b", "2": "c", "3": "d"},
            "probabilities": {"0": 0.1, "1": 0.6, "2": 0.3, "3": 0.0},
        },
        "kb_article": {
            "type": "choice",
            "choice": "api_reference",
            "confidence": 0.77,
            "probabilities": {"api_reference": 1.0},
        },
    }


def test_triager_sends_one_typed_request_per_ticket_and_parses_answers() -> None:
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(
            200,
            json={
                "model": "jev-1.13.0",
                "answers": _answers("auth"),
                "usage": {"input_tokens": 410, "output_tokens": 9},
            },
        )

    async def run() -> list:
        async with AsyncTypeSafeClient(api_key="test-key", transport=httpx2.MockTransport(handler)) as client:
            return await Triager(client, concurrency=2).triage_all(
                [make_ticket(id="T-1"), make_ticket(id="T-2", notes=("internal: VIP, do not share",))]
            )

    triages = asyncio.run(run())

    assert len(seen) == 2
    request = seen[0]
    assert request.method == "POST"
    assert request.url.path == "/v1/systemone"
    assert request.headers["authorization"] == "Bearer test-key"
    body = json.loads(request.content)
    assert set(body["questions"]) == set(QUESTIONS)
    assert {name: q["type"] for name, q in body["questions"].items()} == {
        "queue": "choice",
        "severity": "score",
        "blocked": "noul",
        "needs_engineering": "noul",
        "missing_diagnostics": "noul",
        "frustration": "score",
        "kb_article": "choice",
    }
    assert set(body["questions"]["queue"]["criteria"]) == set(QUEUES)
    # Only the customer's words reach the model; internal notes and metadata stay out of state.
    assert body["state"] == {"subject": "401 after key rotation", "message": "Everything returns 401."}
    assert "VIP" not in seen[1].content.decode()

    tr = triages[0]
    assert (tr.ticket_id, tr.queue, tr.model, tr.input_tokens) == ("T-1", "auth", "jev-1.13.0", 410)
    assert tr.queue_confidence == 0.82 and tr.blocked == 0.93 and tr.severity == 2.7
    decision = decide(tr, make_ticket())
    assert decision.route == "auth" and decision.priority == "P1"
    assert decision.kb_url == "https://docs.typesafe.ai/api"
