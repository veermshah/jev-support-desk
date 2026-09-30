"""Measure triage against labeled tickets before trusting it with a live queue.

Reports accuracy against the legacy keyword router, the accuracy/coverage trade-off at each routing
threshold, and calibration of the yes/no signals — the evidence for picking `Thresholds`.
"""

import statistics
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from jev_support_desk.legacy_router import legacy_route
from jev_support_desk.tickets import Labels, Ticket
from jev_support_desk.triage import Triage

ROUTE_THRESHOLDS = (0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
NOUL_FIELDS: tuple[tuple[str, Callable[[Labels], bool], Callable[[Triage], float]], ...] = (
    ("blocked", lambda lab: lab.blocked, lambda tr: tr.blocked),
    ("needs_engineering", lambda lab: lab.needs_engineering, lambda tr: tr.needs_engineering),
    ("missing_diagnostics", lambda lab: lab.missing_diagnostics, lambda tr: tr.missing_diagnostics),
)
CALIBRATION_BINS = ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0001))


@dataclass(frozen=True)
class ThresholdRow:
    threshold: float
    coverage: float
    accuracy_auto: float | None
    auto_count: int


@dataclass(frozen=True)
class NoulMetrics:
    name: str
    accuracy: float
    brier: float
    bins: list[tuple[str, int, float | None, float | None]]


@dataclass(frozen=True)
class EvalReport:
    n: int
    jev_accuracy: float
    legacy_accuracy: float
    thresholds: list[ThresholdRow]
    nouls: list[NoulMetrics]
    severity_mae: float
    severity_exact: float
    confusion: Counter[tuple[str, str]]
    latency_p50: float
    latency_p95: float
    input_tokens: int
    misses: list[tuple[str, str, str, float]]


def _labeled(tickets: Sequence[Ticket], triages: Sequence[Triage]) -> list[tuple[Ticket, Labels, Triage]]:
    by_id = {t.ticket_id: t for t in triages}
    return [(t, t.labels, by_id[t.id]) for t in tickets if t.labels is not None and t.id in by_id]


def _noul(name: str, pairs: list[tuple[bool, float]]) -> NoulMetrics:
    accuracy = sum((p >= 0.5) == y for y, p in pairs) / len(pairs)
    brier = sum((p - y) ** 2 for y, p in pairs) / len(pairs)
    bins = []
    for low, high in CALIBRATION_BINS:
        members = [(y, p) for y, p in pairs if low <= p < high]
        label = f"{low:.1f}–{min(high, 1.0):.1f}"
        if members:
            mean_p = sum(p for _, p in members) / len(members)
            rate = sum(y for y, _ in members) / len(members)
            bins.append((label, len(members), mean_p, rate))
        else:
            bins.append((label, 0, None, None))
    return NoulMetrics(name, accuracy, brier, bins)


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return ordered[index]


def evaluate(tickets: Sequence[Ticket], triages: Sequence[Triage]) -> EvalReport:
    rows = _labeled(tickets, triages)
    if not rows:
        raise ValueError("No labeled tickets with triage results to evaluate.")
    n = len(rows)
    thresholds = []
    for threshold in ROUTE_THRESHOLDS:
        auto = [(lab, tr) for _, lab, tr in rows if tr.queue_confidence >= threshold]
        correct = sum(tr.queue == lab.queue for lab, tr in auto)
        thresholds.append(ThresholdRow(threshold, len(auto) / n, correct / len(auto) if auto else None, len(auto)))
    nouls = [_noul(name, [(label(lab), prob(tr)) for _, lab, tr in rows]) for name, label, prob in NOUL_FIELDS]
    latencies = [tr.latency_ms for _, _, tr in rows]
    return EvalReport(
        n=n,
        jev_accuracy=sum(tr.queue == lab.queue for _, lab, tr in rows) / n,
        legacy_accuracy=sum(legacy_route(t) == lab.queue for t, lab, _ in rows) / n,
        thresholds=thresholds,
        nouls=nouls,
        severity_mae=statistics.fmean(abs(tr.severity - lab.severity) for _, lab, tr in rows),
        severity_exact=sum(round(tr.severity) == lab.severity for _, lab, tr in rows) / n,
        confusion=Counter((lab.queue, tr.queue) for _, lab, tr in rows if lab.queue != tr.queue),
        latency_p50=_percentile(latencies, 0.5),
        latency_p95=_percentile(latencies, 0.95),
        input_tokens=sum(tr.input_tokens or 0 for _, _, tr in rows),
        misses=[(t.id, lab.queue, tr.queue, tr.queue_confidence) for t, lab, tr in rows if lab.queue != tr.queue],
    )


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.0%}"


def render_report(report: EvalReport, model: str) -> str:
    out = [
        f"# Triage evaluation — {model}",
        "",
        f"{report.n} labeled tickets. Latency p50 {report.latency_p50:.0f} ms, p95 {report.latency_p95:.0f} ms "
        f"(one request per ticket, 7 questions each). {report.input_tokens:,} input tokens total.",
        "",
        "## Queue routing",
        "",
        "| Router | Accuracy |",
        "| --- | --- |",
        f"| Legacy keyword rules | {_pct(report.legacy_accuracy)} |",
        f"| Jev (route everything) | {_pct(report.jev_accuracy)} |",
        "",
        "### Confidence gate: auto-route only when `queue.confidence >= threshold`",
        "",
        "| Threshold | Auto-routed | Accuracy on auto-routed | Sent to human review |",
        "| --- | --- | --- | --- |",
    ]
    out.extend(
        f"| {row.threshold:.1f} | {row.auto_count} ({_pct(row.coverage)}) | {_pct(row.accuracy_auto)} "
        f"| {report.n - row.auto_count} |"
        for row in report.thresholds
    )
    out += [
        "",
        "## Yes/no signals (threshold 0.5)",
        "",
        "| Signal | Accuracy | Brier (lower is better) |",
        "| --- | --- | --- |",
    ]
    out.extend(f"| `{m.name}` | {_pct(m.accuracy)} | {m.brier:.3f} |" for m in report.nouls)
    out += ["", "### Calibration: when Jev says p, how often is the label true?", ""]
    for m in report.nouls:
        out += [f"**`{m.name}`**", "", "| p bucket | n | mean p | observed rate |", "| --- | --- | --- | --- |"]
        out.extend(
            f"| {label} | {count} | {'—' if mean_p is None else f'{mean_p:.2f}'} | {_pct(rate)} |"
            for label, count, mean_p, rate in m.bins
        )
        out.append("")
    out += [
        "## Severity (0–3 rubric)",
        "",
        f"Mean absolute error {report.severity_mae:.2f} levels; rounded score matches the label "
        f"{_pct(report.severity_exact)} of the time.",
        "",
        "## Routing misses",
        "",
    ]
    if report.misses:
        out += ["| Ticket | Label | Jev | Confidence |", "| --- | --- | --- | --- |"]
        out.extend(f"| {tid} | `{label}` | `{got}` | {conf:.2f} |" for tid, label, got, conf in report.misses)
    else:
        out.append("None.")
    out.append("")
    return "\n".join(out)
