from jev_support_desk.doctor import check_headers, check_request, explain_status, repro_curl

VALID = {
    "model": "jev-latest",
    "state": "I was charged twice.",
    "questions": {
        "billing": {"type": "noul", "instructions": "Is this about billing?"},
        "tone": {"type": "choice", "instructions": "What is the tone?", "criteria": {"calm": None, "angry": None}},
        "urgency": {"type": "score", "instructions": "How urgent?", "criteria": ["low", "medium", "high"]},
    },
}


def _errors(findings: list) -> set[str]:
    return {f.path for f in findings if f.level == "error"}


def test_valid_request_is_clean() -> None:
    assert check_request(VALID) == []


def test_missing_fields() -> None:
    assert _errors(check_request({})) >= {"state", "model", "questions"}


def test_empty_score_criteria_is_an_error() -> None:
    body = {**VALID, "questions": {"p": {"type": "score", "criteria": []}}}
    assert "questions.p.criteria" in _errors(check_request(body))


def test_limits_on_options_and_levels() -> None:
    choice = {"type": "choice", "criteria": {f"o{i}": None for i in range(256)}}
    score = {"type": "score", "criteria": [str(i) for i in range(11)]}
    errors = _errors(check_request({**VALID, "questions": {"c": choice, "s": score}}))
    assert {"questions.c.criteria", "questions.s.criteria"} <= errors


def test_unknown_type_and_bad_noul_keys() -> None:
    body = {
        **VALID,
        "questions": {"x": {"type": "bool"}, "n": {"type": "noul", "criteria": {"yes": "..."}}},
    }
    errors = _errors(check_request(body))
    assert "questions.x.type" in errors
    assert any(p.startswith("questions.n.criteria") for p in errors)


def test_unrecognised_model_is_a_warning() -> None:
    findings = check_request({**VALID, "model": "gpt-4"})
    assert [f.level for f in findings if f.path == "model"] == ["warning"]


def test_header_checks() -> None:
    assert check_headers({"Authorization": "Bearer abc", "Content-Type": "application/json"}) == []
    assert "headers.Authorization" in _errors(check_headers({"Content-Type": "application/json"}))
    assert "headers.Authorization" in _errors(check_headers({"authorization": "abc"}))
    assert "headers.Authorization" in _errors(check_headers({"Authorization": "Bearer abc "}))


def test_status_explanations_cover_documented_errors() -> None:
    for status in (401, 403, 404, 422, 429, 529, 500):
        assert explain_status(status)


def test_repro_curl_never_embeds_a_key() -> None:
    curl = repro_curl(VALID)
    assert "$TYPESAFE_API_KEY" in curl
    assert "https://api.typesafe.ai/v1/systemone" in curl
