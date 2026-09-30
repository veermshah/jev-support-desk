"""Support queues, severity rubric, and knowledge-base articles the triage questions choose from."""

DOCS = "https://docs.typesafe.ai"

QUEUES: dict[str, str] = {
    "auth": "API keys and authentication: 401/403 responses, missing or malformed Authorization Bearer header, "
    "rotated or revoked keys, TYPESAFE_API_KEY not being read",
    "request_validation": "The API rejected the request body with 422: missing model, malformed questions, "
    "wrong question type, bad criteria (too many Choice options, Score levels), invalid state shape",
    "rate_limits_capacity": "429 Too Many Requests, 529 Overloaded, throughput limits, retry/backoff behaviour, "
    "timeouts caused by load",
    "sdk_integration": "Installing or using the Python or JavaScript SDK, Vercel AI Gateway, OpenRouter, LangChain or "
    "MCP integrations: import errors, version conflicts, typing, async usage",
    "model_behavior": "The request succeeds but the answers look wrong, probabilities or confidence seem off, "
    "or the customer wants help designing questions and thresholds",
    "bug_or_outage": "Platform-side failures: 5xx errors, malformed responses from the API, sudden regressions or "
    "outages across many requests that the customer did not cause",
    "billing": "Invoices, charges, refunds, usage-based pricing, payment methods, plan changes",
    "account_access": "Console login, SSO, waitlist or early-access status, team members, permission to create keys",
    "product_question": "General how-to or capability questions, feature requests, roadmap, model availability",
}

SEVERITY_LEVELS: list[str] = [
    "Question or feature request with no impact on the customer's work",
    "Degraded experience or inconvenience, but a workaround exists",
    "Blocked in development or testing; nothing in production is affected",
    "Production traffic is failing or the customer's own users or revenue are affected right now",
]

FRUSTRATION_LEVELS: list[str] = ["Calm", "Frustrated", "Very angry or threatening to leave"]

KB_ARTICLES: dict[str, str] = {
    "api_reference": f"{DOCS}/api",
    "quickstart": f"{DOCS}/introduction/quickstart",
    "python_sdk": f"{DOCS}/sdk/python",
    "javascript_sdk": f"{DOCS}/sdk/javascript",
    "retries": f"{DOCS}/sdk/python/api/retries",
    "exceptions": f"{DOCS}/sdk/python/api/exceptions",
    "confidence": f"{DOCS}/confidence",
    "confidence_routing": f"{DOCS}/patterns/confidence-routing",
    "primitives": f"{DOCS}/primitives",
    "models": f"{DOCS}/models",
    "jaggedness": f"{DOCS}/model-jaggedness/jev-1.13",
}

KB_DESCRIPTIONS: dict[str, str | None] = {
    "api_reference": "HTTP endpoint, request/response body, required fields, error status codes",
    "quickstart": "Getting a key and making the first request",
    "python_sdk": "Installing and configuring the Python SDK (typesafe-sdk)",
    "javascript_sdk": "Installing and configuring the JavaScript SDK",
    "retries": "RetryPolicy, backoff and retrying 429/529 responses",
    "exceptions": "SDK exception classes and how to handle API errors",
    "confidence": "What confidence means and how it differs from probability",
    "confidence_routing": "Using confidence thresholds to decide when to automate vs. send to review",
    "primitives": "Choosing between Choice, Score and Noul questions and their limits",
    "models": "Available model names, aliases, and context limits",
    "jaggedness": "Known model weaknesses: math, dates, counting, literal reading, large state",
    "none": "No documentation article would help; this needs a person (billing, account, outage, bug)",
}

DIAGNOSTICS_CHECKLIST: dict[str, list[str]] = {
    "auth": [
        "The exact status code and response body",
        "How the key is supplied (TYPESAFE_API_KEY env var, api_key=..., raw Authorization header)",
        "The last 4 characters of the key and when it was created (never the full key)",
        "The x-typesafe-request-id response header",
    ],
    "request_validation": [
        "The full request body you sent, with the Authorization header removed",
        "The full 422 response body (it names the offending field)",
        "SDK name and version, or the raw HTTP client you use",
    ],
    "rate_limits_capacity": [
        "Approximate requests per second and concurrency at the time of the errors",
        "The time window (with time zone) and the share of requests that returned 429/529",
        "Whether you use the SDK's default RetryPolicy or custom retry logic",
        "A few x-typesafe-request-id values from failed requests",
    ],
    "sdk_integration": [
        "SDK name and version (pip show typesafe-sdk / npm ls), and runtime version",
        "A minimal code sample that reproduces the problem",
        "The full stack trace",
    ],
    "model_behavior": [
        "The request body (state and questions) and the response you received",
        "The answer you expected and why",
        "The model name from the response (e.g. jev-1.13.0)",
    ],
    "bug_or_outage": [
        "The time window (with time zone) when the failures started",
        "Status codes and a few x-typesafe-request-id values",
        "Whether any recent change was made on your side",
    ],
    "billing": ["The invoice number or charge date and amount (no card details)"],
    "account_access": ["The email address on the account and the exact error shown in the console"],
    "product_question": [],
}
