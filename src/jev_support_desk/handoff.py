"""Shift handover: what is still open, who is blocked, and which promises come due next shift."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from jev_support_desk.tickets import Ticket
from jev_support_desk.triage import DEFAULT_THRESHOLDS, Decision, Thresholds, Triage, is_misrouted

PRIORITY_ORDER = {"P1": 0, "P2": 1, "P3": 2}


@dataclass(frozen=True)
class Row:
    ticket: Ticket
    triage: Triage
    decision: Decision


def _due(ticket: Ticket, now: datetime, horizon: timedelta) -> str | None:
    if ticket.promised_update_at is None:
        return None
    if ticket.promised_update_at <= now:
        return f"OVERDUE by {_fmt_delta(now - ticket.promised_update_at)}"
    if ticket.promised_update_at <= now + horizon:
        return f"due in {_fmt_delta(ticket.promised_update_at - now)}"
    return None


def _fmt_delta(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    return f"{minutes // 60}h{minutes % 60:02d}m"


def _line(row: Row, now: datetime, horizon: timedelta) -> str:
    t, tr, d = row.ticket, row.triage, row.decision
    parts = [
        f"**{t.id}** [{d.priority}] {t.subject}",
        f"queue `{d.route}` ({tr.queue_confidence:.2f})",
        f"blocked {tr.blocked:.2f}",
        f"tier {t.customer_tier}",
    ]
    if t.owner:
        parts.append(f"owner {t.owner}")
    due = _due(t, now, horizon)
    if due:
        parts.append(f"update {due}")
    if d.uncertain:
        parts.append("unsure: " + ", ".join(d.uncertain))
    return "- " + " · ".join(parts)


def render_handoff(
    rows: Sequence[Row],
    now: datetime,
    shift: str,
    horizon: timedelta = timedelta(hours=8),
    thresholds: Thresholds = DEFAULT_THRESHOLDS,
) -> str:
    open_rows = sorted(
        (r for r in rows if r.ticket.status != "resolved"),
        key=lambda r: (PRIORITY_ORDER[r.decision.priority], -r.triage.blocked, r.ticket.created_at or now),
    )
    sections: list[tuple[str, list[Row]]] = [
        ("Blocked customers (handle first)", [r for r in open_rows if r.triage.blocked >= thresholds.blocked]),
        ("Promised updates overdue or due this shift", [r for r in open_rows if _due(r.ticket, now, horizon)]),
        ("Waiting on engineering", [r for r in open_rows if r.ticket.status == "pending_engineering"]),
        (
            "Needs engineering escalation (not yet handed off)",
            [
                r
                for r in open_rows
                if "escalate_to_engineering" in r.decision.actions and r.ticket.status != "pending_engineering"
            ],
        ),
        ("Needs a human routing decision", [r for r in open_rows if not r.decision.auto_routed]),
        ("Waiting on customer", [r for r in open_rows if r.ticket.status == "pending_customer"]),
    ]
    misrouted = [r for r in open_rows if is_misrouted(r.triage, r.ticket, thresholds)]

    counts = {p: sum(r.decision.priority == p for r in open_rows) for p in PRIORITY_ORDER}
    out = [
        f"# Shift handoff — {shift}",
        "",
        f"Generated {now.strftime('%Y-%m-%d %H:%M %Z')}. {len(open_rows)} open tickets "
        f"({counts['P1']} P1, {counts['P2']} P2, {counts['P3']} P3).",
        "",
    ]
    for title, section in sections:
        out.append(f"## {title} ({len(section)})")
        out.extend(_line(r, now, horizon) for r in section)
        if not section:
            out.append("- none")
        out.append("")
    out.append(f"## Possible misroutes ({len(misrouted)})")
    out.extend(
        f"- **{r.ticket.id}** assigned `{r.ticket.assigned_queue}`, Jev says `{r.triage.queue}` "
        f"({r.triage.queue_confidence:.2f})"
        for r in misrouted
    )
    if not misrouted:
        out.append("- none")
    out.append("")
    out.append("## Suggested next actions")
    for r in open_rows:
        if not r.decision.actions:
            continue
        extras = []
        if r.decision.ask_for:
            extras.append("ask for: " + "; ".join(r.decision.ask_for))
        if r.decision.kb_url:
            extras.append(f"doc: {r.decision.kb_url}")
        suffix = f" — {' | '.join(extras)}" if extras else ""
        out.append(f"- **{r.ticket.id}**: {', '.join(r.decision.actions)}{suffix}")
    out.append("")
    return "\n".join(out)
