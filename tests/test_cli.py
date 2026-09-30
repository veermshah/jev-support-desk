import json
from dataclasses import asdict
from pathlib import Path

import pytest

from jev_support_desk.cli import main
from jev_support_desk.tickets import load_tickets
from tests.helpers import make_triage

ROOT = Path(__file__).resolve().parents[1]


def test_doctor_flags_the_empty_score(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["doctor", str(ROOT / "examples/422_empty_score.json")])
    out = capsys.readouterr().out
    assert exit_info.value.code == 1
    assert "questions.priority.criteria" in out
    assert "HTTP 422" in out
    assert "$TYPESAFE_API_KEY" in out
    assert "ts_live" not in out


def test_doctor_flags_the_bad_auth_header(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["doctor", str(ROOT / "examples/401_bad_header.json")])
    out = capsys.readouterr().out
    assert "headers.Authorization" in out
    assert "questions.outage.criteria.yes" in out
    assert "HTTP 401" in out


def test_handoff_and_eval_from_cache(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tickets = load_tickets(ROOT / "data/tickets.jsonl")
    cache = tmp_path / "triage.json"
    cache.write_text(
        json.dumps([asdict(make_triage(ticket_id=t.id, queue=t.labels.queue)) for t in tickets if t.labels])
    )
    main(["handoff", str(ROOT / "data/tickets.jsonl"), "--cache", str(cache), "--now", "2026-09-30T21:00Z"])
    handoff = capsys.readouterr().out
    assert f"{len(tickets)} open tickets" in handoff
    assert "## Possible misroutes" in handoff

    main(["eval", str(ROOT / "data/tickets.jsonl"), "--cache", str(cache)])
    report = capsys.readouterr().out
    assert "| Jev (route everything) | 100% |" in report
