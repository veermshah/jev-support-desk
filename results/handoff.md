# Shift handoff — US → EU

Generated 2026-09-30 21:00 UTC. 36 open tickets (5 P1, 17 P2, 14 P3).

## Blocked customers (handle first) (13)
- **T-1026** [P1] Payment failed, account suspended? · queue `billing` (1.00) · blocked 0.88 · tier pro
- **T-1001** [P1] All requests failing since this morning · queue `bug_or_outage` (1.00) · blocked 0.78 · tier enterprise · owner veer · update OVERDUE by 1h00m
- **T-1013** [P1] 529 Overloaded across all regions · queue `rate_limits_capacity` (0.71) · blocked 0.78 · tier enterprise · update due in 2h00m
- **T-1008** [P2] Can't log in to console · queue `account_access` (1.00) · blocked 0.91 · tier free · unsure: needs_engineering
- **T-1003** [P2] it doesn't work · queue `bug_or_outage` (0.77) · blocked 0.81 · tier free
- **T-1002** [P2] 401 after rotating key · queue `auth` (1.00) · blocked 0.79 · tier pro
- **T-1023** [P2] Add teammate to org · queue `account_access` (1.00) · blocked 0.76 · tier enterprise · owner maria · update due in 0h30m · unsure: missing_diagnostics
- **T-1031** [P2] Getting an error in my integration · queue `sdk_integration` (0.84) · blocked 0.73 · tier pro · unsure: needs_engineering
- **T-1029** [P2] 403 on /v1/models · queue `auth` (0.97) · blocked 0.64 · tier free · unsure: blocked
- **T-1009** [P2] ImportError with typesafe_sdk · queue `sdk_integration` (1.00) · blocked 0.60 · tier pro · unsure: blocked, needs_engineering
- **T-1019** [P2] Model name not found · queue `triage_review` (0.56) · blocked 0.59 · tier pro · unsure: blocked
- **T-1017** [P2] Bearer token question · queue `auth` (0.98) · blocked 0.55 · tier pro · unsure: blocked
- **T-1004** [P2] 422 when adding a fourth question · queue `request_validation` (0.99) · blocked 0.53 · tier pro · unsure: blocked

## Promised updates overdue or due this shift (5)
- **T-1001** [P1] All requests failing since this morning · queue `bug_or_outage` (1.00) · blocked 0.78 · tier enterprise · owner veer · update OVERDUE by 1h00m
- **T-1013** [P1] 529 Overloaded across all regions · queue `rate_limits_capacity` (0.71) · blocked 0.78 · tier enterprise · update due in 2h00m
- **T-1005** [P1] Choice probabilities don't sum to 1 · queue `bug_or_outage` (0.65) · blocked 0.36 · tier enterprise · owner maria · update due in 1h00m · unsure: blocked
- **T-1023** [P2] Add teammate to org · queue `account_access` (1.00) · blocked 0.76 · tier enterprise · owner maria · update due in 0h30m · unsure: missing_diagnostics
- **T-1012** [P2] Wrong answers on refund detection · queue `model_behavior` (0.99) · blocked 0.18 · tier pro · owner veer · update OVERDUE by 3h00m · unsure: needs_engineering

## Waiting on engineering (1)
- **T-1005** [P1] Choice probabilities don't sum to 1 · queue `bug_or_outage` (0.65) · blocked 0.36 · tier enterprise · owner maria · update due in 1h00m · unsure: blocked

## Needs engineering escalation (not yet handed off) (2)
- **T-1001** [P1] All requests failing since this morning · queue `bug_or_outage` (1.00) · blocked 0.78 · tier enterprise · owner veer · update OVERDUE by 1h00m
- **T-1013** [P1] 529 Overloaded across all regions · queue `rate_limits_capacity` (0.71) · blocked 0.78 · tier enterprise · update due in 2h00m

## Needs a human routing decision (1)
- **T-1019** [P2] Model name not found · queue `triage_review` (0.56) · blocked 0.59 · tier pro · unsure: blocked

## Waiting on customer (1)
- **T-1012** [P2] Wrong answers on refund detection · queue `model_behavior` (0.99) · blocked 0.18 · tier pro · owner veer · update OVERDUE by 3h00m · unsure: needs_engineering

## Possible misroutes (9)
- **T-1028** assigned `rate_limits_capacity`, Jev says `bug_or_outage` (0.99)
- **T-1005** assigned `sdk_integration`, Jev says `bug_or_outage` (0.65)
- **T-1003** assigned `product_question`, Jev says `bug_or_outage` (0.77)
- **T-1023** assigned `product_question`, Jev says `account_access` (1.00)
- **T-1020** assigned `product_question`, Jev says `model_behavior` (0.95)
- **T-1012** assigned `billing`, Jev says `model_behavior` (0.99)
- **T-1021** assigned `product_question`, Jev says `rate_limits_capacity` (0.60)
- **T-1035** assigned `product_question`, Jev says `billing` (1.00)
- **T-1032** assigned `billing`, Jev says `model_behavior` (0.99)

## Suggested next actions
- **T-1001**: escalate_to_engineering
- **T-1013**: escalate_to_engineering, suggest_kb_article — doc: https://docs.typesafe.ai/sdk/python/api/retries
- **T-1005**: escalate_to_engineering
- **T-1003**: request_diagnostics, suggest_kb_article — ask for: The time window (with time zone) when the failures started; Status codes and a few x-typesafe-request-id values; Whether any recent change was made on your side | doc: https://docs.typesafe.ai/api
- **T-1002**: suggest_kb_article — doc: https://docs.typesafe.ai/introduction/quickstart
- **T-1031**: request_diagnostics, suggest_kb_article — ask for: SDK name and version (pip show typesafe-sdk / npm ls), and runtime version; A minimal code sample that reproduces the problem; The full stack trace | doc: https://docs.typesafe.ai/sdk/python/api/exceptions
- **T-1029**: suggest_kb_article — doc: https://docs.typesafe.ai/api
- **T-1009**: suggest_kb_article — doc: https://docs.typesafe.ai/sdk/python
- **T-1019**: human_routing_review, suggest_kb_article — doc: https://docs.typesafe.ai/models
- **T-1017**: suggest_kb_article — doc: https://docs.typesafe.ai/api
- **T-1004**: suggest_kb_article — doc: https://docs.typesafe.ai/api
- **T-1024**: suggest_kb_article — doc: https://docs.typesafe.ai/primitives
- **T-1007**: suggest_kb_article — doc: https://docs.typesafe.ai/sdk/python/api/retries
- **T-1033**: suggest_kb_article — doc: https://docs.typesafe.ai/introduction/quickstart
- **T-1022**: suggest_kb_article — doc: https://docs.typesafe.ai/api
- **T-1020**: suggest_kb_article — doc: https://docs.typesafe.ai/model-jaggedness/jev-1.13
- **T-1012**: request_diagnostics, suggest_kb_article — ask for: The request body (state and questions) and the response you received; The answer you expected and why; The model name from the response (e.g. jev-1.13.0) | doc: https://docs.typesafe.ai/primitives
- **T-1036**: suggest_kb_article — doc: https://docs.typesafe.ai/api
- **T-1021**: request_diagnostics, suggest_kb_article — ask for: Approximate requests per second and concurrency at the time of the errors; The time window (with time zone) and the share of requests that returned 429/529; Whether you use the SDK's default RetryPolicy or custom retry logic; A few x-typesafe-request-id values from failed requests | doc: https://docs.typesafe.ai/sdk/python/api/retries
- **T-1027**: suggest_kb_article — doc: https://docs.typesafe.ai/sdk/javascript
- **T-1011**: suggest_kb_article — doc: https://docs.typesafe.ai/api
- **T-1010**: suggest_kb_article — doc: https://docs.typesafe.ai/confidence
- **T-1014**: suggest_kb_article — doc: https://docs.typesafe.ai/api
- **T-1034**: suggest_kb_article — doc: https://docs.typesafe.ai/models
- **T-1025**: suggest_kb_article — doc: https://docs.typesafe.ai/patterns/confidence-routing
- **T-1032**: suggest_kb_article — doc: https://docs.typesafe.ai/patterns/confidence-routing
