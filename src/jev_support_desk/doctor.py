"""Check a customer's System One request (and optionally the error they got) before anyone else has to.

Checks follow the published API reference and OpenAPI schema (https://api.typesafe.ai/openapi.json). The
doctor runs offline; `repro_curl` produces a key-free command support can run with their own key.
"""

import json
import re
import shlex
from dataclasses import dataclass
from typing import Any

MAX_CHOICE_OPTIONS = 255
MAX_SCORE_LEVELS = 10
QUESTION_TYPES = {"noul", "choice", "score"}
QUESTION_FIELDS = {"type", "instructions", "criteria"}
TOP_LEVEL_FIELDS = {"state", "model", "questions"}
KNOWN_MODEL = re.compile(r"^jev-(latest|preview|\d+\.\d+(\.\d+)?)$")


@dataclass(frozen=True)
class Finding:
    level: str
    path: str
    message: str


STATUS_GUIDANCE: dict[int, str] = {
    400: "The request could not be parsed. Check the body is valid JSON and Content-Type is application/json.",
    401: "Missing or invalid API key. Send `Authorization: Bearer <key>` (the SDKs read TYPESAFE_API_KEY). "
    "Check for a stray newline or quotes around the key and that the key was not revoked.",
    403: "The key is valid but not allowed to do this. Check the account's access and the model name.",
    404: "Wrong URL. The evaluation endpoint is POST https://api.typesafe.ai/v1/systemone.",
    422: "The body failed validation; the response `detail` names the field. Common causes: missing `model`, "
    "empty `questions`, a Choice without `criteria`, or an empty Score `criteria` list.",
    429: "Rate limit exceeded. Retry with exponential backoff (the SDK's default RetryPolicy does this) and "
    "reduce concurrency; honour retry-after / retry-after-ms headers.",
    529: "TypeSafe is temporarily overloaded. Retry after a short delay with backoff. If it persists across "
    "many request ids, escalate to engineering as a possible incident.",
}


def _check_question(name: str, question: Any) -> list[Finding]:
    path = f"questions.{name}"
    if not isinstance(question, dict):
        return [Finding("error", path, "Each question must be an object with a `type`.")]
    findings = [
        Finding("error", f"{path}.{key}", f"Unknown field `{key}`; questions accept only type, instructions, criteria.")
        for key in question.keys() - QUESTION_FIELDS
    ]
    qtype = question.get("type")
    if qtype not in QUESTION_TYPES:
        findings.append(Finding("error", f"{path}.type", f"`type` must be one of noul, choice, score (got {qtype!r})."))
        return findings
    if not question.get("instructions"):
        findings.append(
            Finding(
                "warning",
                f"{path}.instructions",
                "No instructions. The question id is not shown to the model, so write the full question here.",
            )
        )
    criteria = question.get("criteria")
    if qtype == "choice":
        if not isinstance(criteria, dict) or not criteria:
            findings.append(
                Finding("error", f"{path}.criteria", "A Choice needs `criteria`: a map of option -> description.")
            )
        elif len(criteria) > MAX_CHOICE_OPTIONS:
            findings.append(
                Finding(
                    "error",
                    f"{path}.criteria",
                    f"{len(criteria)} options; a Choice accepts at most {MAX_CHOICE_OPTIONS}.",
                )
            )
        elif len(criteria) == 1:
            findings.append(
                Finding("warning", f"{path}.criteria", "Only one option; use a Noul for a yes/no question.")
            )
    elif qtype == "score":
        if not isinstance(criteria, list) or not criteria:
            findings.append(
                Finding("error", f"{path}.criteria", "A Score needs `criteria`: an ordered list of levels.")
            )
        elif len(criteria) > MAX_SCORE_LEVELS:
            findings.append(
                Finding(
                    "error", f"{path}.criteria", f"{len(criteria)} levels; a Score accepts at most {MAX_SCORE_LEVELS}."
                )
            )
        elif len(criteria) == 1:
            findings.append(Finding("warning", f"{path}.criteria", "A Score should have at least two levels."))
    elif criteria is not None:
        if not isinstance(criteria, dict):
            findings.append(
                Finding("error", f"{path}.criteria", 'Noul criteria must be an object: {"true": ..., "false": ...}.')
            )
        else:
            findings.extend(
                Finding("error", f"{path}.criteria.{key}", "Noul criteria accept only `true` and `false`.")
                for key in criteria.keys() - {"true", "false"}
            )
    return findings


def check_request(body: Any) -> list[Finding]:
    if not isinstance(body, dict):
        return [Finding("error", "", "The request body must be a JSON object with state, model, and questions.")]
    findings = [
        Finding("warning", key, f"Unexpected top-level field `{key}`; the API documents only state, model, questions.")
        for key in body.keys() - TOP_LEVEL_FIELDS
    ]
    if "state" not in body:
        findings.append(
            Finding("error", "state", "Missing `state`: the text, object, or array the questions are about.")
        )
    elif not isinstance(body["state"], (str, dict, list)):
        findings.append(Finding("error", "state", "`state` must be a string, a JSON object, or an array."))
    model = body.get("model")
    if model is None:
        findings.append(
            Finding("error", "model", 'Missing `model`; the API returns 422. Use "jev-latest" or pin a version.')
        )
    elif not isinstance(model, str) or not KNOWN_MODEL.match(model):
        findings.append(
            Finding("warning", "model", f"Unrecognised model {model!r}; check GET /v1/models for valid names.")
        )
    questions = body.get("questions")
    if not isinstance(questions, dict) or not questions:
        findings.append(Finding("error", "questions", "`questions` must be a non-empty map of id -> question."))
    else:
        for name, question in questions.items():
            findings.extend(_check_question(name, question))
    return findings


def check_headers(headers: dict[str, str]) -> list[Finding]:
    lowered = {k.lower(): v for k, v in headers.items()}
    auth = lowered.get("authorization")
    if auth is None:
        return [Finding("error", "headers.Authorization", "No Authorization header; the API will return 401.")]
    findings = []
    if not auth.startswith("Bearer "):
        findings.append(Finding("error", "headers.Authorization", 'Authorization must be "Bearer <key>".'))
    token = auth.removeprefix("Bearer ")
    if token != token.strip() or any(c in token for c in "\"'\n\r\t "):
        findings.append(
            Finding("error", "headers.Authorization", "The key contains whitespace or quotes (copy/paste?).")
        )
    content_type = lowered.get("content-type", "")
    if "application/json" not in content_type:
        findings.append(Finding("warning", "headers.Content-Type", "Set Content-Type: application/json."))
    return findings


def explain_status(status: int) -> str:
    if status in STATUS_GUIDANCE:
        return STATUS_GUIDANCE[status]
    if status >= 500:
        return "Server-side error. Retry once; if it repeats, collect x-typesafe-request-id values and escalate."
    return "No specific guidance for this status."


def repro_curl(body: dict[str, Any], base_url: str = "https://api.typesafe.ai") -> str:
    return (
        f"curl -sS -X POST {base_url}/v1/systemone \\\n"
        '  -H "Authorization: Bearer $TYPESAFE_API_KEY" \\\n'
        '  -H "Content-Type: application/json" \\\n'
        f"  -d {shlex.quote(json.dumps(body, separators=(',', ':')))}"
    )
