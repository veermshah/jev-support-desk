# Triage evaluation — jev-1.13.0

36 labeled tickets. Latency p50 99 ms, p95 141 ms (one request per ticket, 7 questions each). 53,339 input tokens total.

## Queue routing

| Router | Accuracy |
| --- | --- |
| Legacy keyword rules | 75% |
| Jev (route everything) | 92% |

### Confidence gate: auto-route only when `queue.confidence >= threshold`

| Threshold | Auto-routed | Accuracy on auto-routed | Sent to human review |
| --- | --- | --- | --- |
| 0.0 | 36 (100%) | 92% | 0 |
| 0.3 | 36 (100%) | 92% | 0 |
| 0.4 | 36 (100%) | 92% | 0 |
| 0.5 | 36 (100%) | 92% | 0 |
| 0.6 | 35 (97%) | 94% | 1 |
| 0.7 | 32 (89%) | 94% | 4 |
| 0.8 | 29 (81%) | 100% | 7 |
| 0.9 | 27 (75%) | 100% | 9 |

## Yes/no signals (threshold 0.5)

| Signal | Accuracy | Brier (lower is better) |
| --- | --- | --- |
| `blocked` | 94% | 0.093 |
| `needs_engineering` | 86% | 0.094 |
| `missing_diagnostics` | 100% | 0.036 |

### Calibration: when Jev says p, how often is the label true?

**`blocked`**

| p bucket | n | mean p | observed rate |
| --- | --- | --- | --- |
| 0.0–0.2 | 13 | 0.09 | 0% |
| 0.2–0.4 | 8 | 0.30 | 0% |
| 0.4–0.6 | 5 | 0.52 | 60% |
| 0.6–0.8 | 7 | 0.73 | 71% |
| 0.8–1.0 | 3 | 0.87 | 100% |

**`needs_engineering`**

| p bucket | n | mean p | observed rate |
| --- | --- | --- | --- |
| 0.0–0.2 | 17 | 0.11 | 0% |
| 0.2–0.4 | 8 | 0.29 | 0% |
| 0.4–0.6 | 5 | 0.52 | 20% |
| 0.6–0.8 | 3 | 0.62 | 0% |
| 0.8–1.0 | 3 | 0.84 | 100% |

**`missing_diagnostics`**

| p bucket | n | mean p | observed rate |
| --- | --- | --- | --- |
| 0.0–0.2 | 21 | 0.11 | 0% |
| 0.2–0.4 | 11 | 0.27 | 0% |
| 0.4–0.6 | 0 | — | — |
| 0.6–0.8 | 1 | 0.69 | 100% |
| 0.8–1.0 | 3 | 0.89 | 100% |

## Severity (0–3 rubric)

Mean absolute error 0.50 levels; rounded score matches the label 53% of the time.

## Routing misses

| Ticket | Label | Jev | Confidence |
| --- | --- | --- | --- |
| T-1003 | `product_question` | `bug_or_outage` | 0.77 |
| T-1013 | `bug_or_outage` | `rate_limits_capacity` | 0.71 |
| T-1019 | `request_validation` | `product_question` | 0.56 |
