"""Ticket records and JSONL loading."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Labels:
    """Human-assigned ground truth used by the evaluation harness."""

    queue: str
    severity: int
    blocked: bool
    needs_engineering: bool
    missing_diagnostics: bool


@dataclass(frozen=True)
class Ticket:
    id: str
    subject: str
    body: str
    customer_tier: str = "pro"
    status: str = "open"
    created_at: datetime | None = None
    promised_update_at: datetime | None = None
    assigned_queue: str | None = None
    owner: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    labels: Labels | None = None

    def jev_state(self) -> dict[str, str]:
        """Only the fields the triage questions need; routing metadata stays out of the model's view."""
        return {"subject": self.subject, "message": self.body}


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def ticket_from_dict(raw: dict) -> Ticket:
    labels = raw.get("labels")
    return Ticket(
        id=raw["id"],
        subject=raw["subject"],
        body=raw["body"],
        customer_tier=raw.get("customer_tier", "pro"),
        status=raw.get("status", "open"),
        created_at=_parse_dt(raw.get("created_at")),
        promised_update_at=_parse_dt(raw.get("promised_update_at")),
        assigned_queue=raw.get("assigned_queue"),
        owner=raw.get("owner"),
        notes=tuple(raw.get("notes", ())),
        labels=Labels(**labels) if labels else None,
    )


def load_tickets(path: str | Path) -> list[Ticket]:
    lines = Path(path).read_text().splitlines()
    return [ticket_from_dict(json.loads(line)) for line in lines if line.strip()]
