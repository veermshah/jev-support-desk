# Triage evaluation — jev-1.13.0

36 labeled tickets. Latency p50 80 ms, p95 158 ms (one request per ticket, 7 questions each). 52,187 input tokens total.

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
| 0.6 | 34 (94%) | 94% | 2 |
| 0.7 | 31 (86%) | 97% | 5 |
| 0.8 | 30 (83%) | 100% | 6 |
| 0.9 | 27 (75%) | 100% | 9 |

## Yes/no signals (threshold 0.5)

| Signal | Accuracy | Brier (lower is better) |
| --- | --- | --- |
| `blocked` | 92% | 0.091 |
| `needs_engineering` | 86% | 0.094 |
| `missing_diagnostics` | 39% | 0.462 |

### Calibration: when Jev says p, how often is the label true?

**`blocked`**

| p bucket | n | mean p | observed rate |
| --- | --- | --- | --- |
| 0.0–0.2 | 13 | 0.09 | 0% |
| 0.2–0.4 | 8 | 0.30 | 0% |
| 0.4–0.6 | 4 | 0.52 | 50% |
| 0.6–0.8 | 8 | 0.71 | 75% |
| 0.8–1.0 | 3 | 0.87 | 100% |

**`needs_engineering`**

| p bucket | n | mean p | observed rate |
| --- | --- | --- | --- |
| 0.0–0.2 | 16 | 0.10 | 0% |
| 0.2–0.4 | 10 | 0.30 | 0% |
| 0.4–0.6 | 3 | 0.52 | 0% |
| 0.6–0.8 | 4 | 0.61 | 25% |
| 0.8–1.0 | 3 | 0.85 | 100% |

**`missing_diagnostics`**

| p bucket | n | mean p | observed rate |
| --- | --- | --- | --- |
| 0.0–0.2 | 4 | 0.15 | 0% |
| 0.2–0.4 | 2 | 0.22 | 0% |
| 0.4–0.6 | 5 | 0.46 | 0% |
| 0.6–0.8 | 3 | 0.70 | 0% |
| 0.8–1.0 | 22 | 0.89 | 18% |

## Severity (0–3 rubric)

Mean absolute error 0.48 levels; rounded score matches the label 56% of the time.

## Routing misses

| Ticket | Label | Jev | Confidence |
| --- | --- | --- | --- |
| T-1003 | `product_question` | `bug_or_outage` | 0.75 |
| T-1013 | `bug_or_outage` | `rate_limits_capacity` | 0.69 |
| T-1019 | `request_validation` | `product_question` | 0.53 |
