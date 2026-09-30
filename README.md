# jev-support-desk

Developer-support queue tooling built on [TypeSafe's Jev](https://docs.typesafe.ai). It covers the
parts of a support shift that are judgment calls (which queue, how bad, is the customer blocked, does
engineering need to look) and keeps the rest (thresholds, priorities, SLAs, dates) in plain code.

```
jev-desk triage   tickets.jsonl   # one Jev request per ticket -> route, priority, next actions
jev-desk handoff  tickets.jsonl   # end-of-shift handoff: blocked customers, due promises, misroutes
jev-desk eval     tickets.jsonl   # Jev vs. keyword rules on labeled tickets, with a confidence sweep
jev-desk doctor   request.json    # offline check of a customer's failing API request + key-free curl repro
jev-desk models                   # connectivity/auth check against GET /v1/models
```

## Why this shape

- **One request, seven typed questions per ticket.** `triage.py` asks a `Choice` (queue), two `Score`s
  (severity, frustration), three `Noul`s (blocked, needs engineering, missing diagnostics) and a second
  `Choice` (which doc to link) in a single `system_one` call.
- **Confidence decides whether code acts.** Tickets auto-route only when `queue.confidence >= 0.6`;
  everything else goes to `triage_review`. Noul probabilities in the 0.35–0.65 band are flagged as
  "unsure" in the handoff rather than silently acted on
  ([confidence routing](https://docs.typesafe.ai/patterns/confidence-routing)).
- **Jev judges, code decides.** Priority (P1/P2/P3), escalation, which diagnostics to ask for, and all date
  arithmetic for promised updates live in Python — the kind of work the
  [model-jaggedness notes](https://docs.typesafe.ai/model-jaggedness/jev-1.13) say not to hand to Jev.
- **Only the customer's words reach the model.** `Ticket.jev_state()` sends `{subject, message}`; internal
  notes, owner, tier and timestamps never enter `state`.
- **Measured, not assumed.** `jev-desk eval` compares Jev to the legacy keyword router and sweeps the
  confidence threshold so the auto-route/human-review trade-off is a number, not a feeling.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env            # set TYPESAFE_API_KEY
export $(grep -v '^#' .env | xargs)

jev-desk models                                  # confirms the key works
jev-desk eval data/tickets.jsonl --out out/eval.md
jev-desk triage data/tickets.jsonl               # reuses out/triage.json; --refresh to call Jev again
jev-desk handoff data/tickets.jsonl --shift "US → EU" --out out/handoff.md
```

Triage results are cached in `out/triage.json`, so `triage`, `handoff` and `eval` share one set of Jev calls.

## Request doctor (works without a key)

`jev-desk doctor` takes what a customer pastes into a ticket — request body, headers, and the response
they got — and checks it against the [API reference](https://docs.typesafe.ai/api) before anyone
has to reproduce it:

```
$ jev-desk doctor examples/401_bad_header.json
[ERROR  ] questions.outage.criteria.yes: Noul criteria accept only `true` and `false`.
[WARNING] questions.team.criteria: Only one option; use a Noul for a yes/no question.
[ERROR  ] headers.Authorization: Authorization must be "Bearer <key>".
[ERROR  ] headers.Authorization: The key contains whitespace or quotes (copy/paste?).
[WARNING] headers.Content-Type: Set Content-Type: application/json.

HTTP 401: Missing or invalid API key. Send `Authorization: Bearer <key>` (the SDKs read TYPESAFE_API_KEY). ...

Reproduce with your own key:

curl -sS -X POST https://api.typesafe.ai/v1/systemone \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"jev-1.13","state":"Our checkout is failing with a 500.", ...}'
```

It checks required fields, question types, Choice/Score/Noul criteria shapes and limits, the
Authorization header, and explains 401/403/404/422/429/529/5xx. The repro never contains the customer's key.

## Data

`data/tickets.jsonl` holds 36 synthetic developer-support tickets (auth, 422s, 429/529, SDK issues,
model-behaviour questions, outages, billing, account access), each hand-labeled with queue, severity,
blocked, needs-engineering and missing-diagnostics. Several are written to trip keyword rules — e.g. a
refund question caused by an outage, or "wrong answers on refund detection", which is a model-behaviour
ticket, not billing. Regenerate with `python data/build_tickets.py`.

Baseline: the legacy keyword router (`legacy_router.py`) gets **27/36 (75%)** of queues right.

## Results with Jev

Live run on 2026-09-30 against `jev-latest` (resolved to `jev-1.13.0`), 36 tickets, one request per ticket
with all seven questions. Full reports: [`results/eval.md`](results/eval.md),
[`results/handoff.md`](results/handoff.md), [`results/triage.txt`](results/triage.txt).

| | Keyword rules | Jev |
| --- | --- | --- |
| Queue accuracy (route everything) | 75% (27/36) | **92% (33/36)** |
| Accuracy when auto-routing at confidence ≥ 0.8 | — | **100%** on 81% of tickets; 7 go to a human |
| `blocked` / `needs_engineering` accuracy (p ≥ 0.5) | — | 94% / 86% |
| Latency p50 / p95 | — | 99 ms / 141 ms |

The three routing misses are all defensible calls on ambiguous tickets (a vague "it doesn't work" routed
to `bug_or_outage`, a 529 incident routed to `rate_limits_capacity`, a bad model name) and two of them
fall below the 0.8 gate, so they would have gone to human review rather than being misrouted.

### Fixing a question that didn't work

The first run exposed a bad question. `missing_diagnostics` asked whether the message was "missing details
support would need … such as the status code, error body, request body, code sample, SDK version, or
request id". Jev read that literally: almost every ticket lacks *some* item on that list, so it said
yes (p ≈ 0.89) for 22 of 36 tickets and scored **39%** accuracy with a Brier score of 0.46
([`results/eval-v1-missing-diagnostics-original.md`](results/eval-v1-missing-diagnostics-original.md)).

The rewrite asks the decision support actually makes — *would we have to reply asking for more information
before anyone could investigate?* — and gives concrete `true`/`false` criteria. Same tickets, same model:
**100%** accuracy, Brier 0.036, and nothing left in the 0.4–0.6 "unsure" band.

Caveat: the rewrite was tuned on the same 36 tickets it was scored on, so treat that number as "the
question now means what we intended", not as a held-out accuracy estimate.

## Layout

| File | What it does |
| --- | --- |
| `src/jev_support_desk/triage.py` | Jev questions, `Triager` (async, bounded concurrency), `decide()` policy, misroute check |
| `src/jev_support_desk/taxonomy.py` | Queues, severity rubric, doc links, per-queue diagnostics checklists |
| `src/jev_support_desk/handoff.py` | Markdown shift handoff |
| `src/jev_support_desk/evaluate.py` | Accuracy, confidence sweep, Brier scores, calibration, latency, tokens |
| `src/jev_support_desk/doctor.py` | Offline request/headers/status checker + curl repro |
| `src/jev_support_desk/legacy_router.py` | Keyword baseline and default "current assignment" for misroute detection |
| `tests/` | Policy, doctor, handoff, eval, CLI, and the real `typesafe-sdk` client against a mocked transport |

## Development

```bash
ruff check . && ruff format --check . && pytest -q
```

Tests don't need a key: `tests/test_sdk_integration.py` runs the real `AsyncTypeSafeClient` over an
`httpx2.MockTransport` and asserts on the exact HTTP request (path, Bearer header, question types, state).
