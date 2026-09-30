"""`jev-desk` command line."""

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from typesafe_sdk import AsyncTypeSafeClient, TypeSafeClient, TypeSafeError

from jev_support_desk.doctor import check_headers, check_request, explain_status, repro_curl
from jev_support_desk.evaluate import evaluate, render_report
from jev_support_desk.handoff import Row, render_handoff
from jev_support_desk.legacy_router import legacy_route
from jev_support_desk.tickets import Ticket, load_tickets
from jev_support_desk.triage import DEFAULT_THRESHOLDS, Triage, Triager, decide


def _with_assignments(tickets: list[Ticket]) -> list[Ticket]:
    return [t if t.assigned_queue else replace(t, assigned_queue=legacy_route(t)) for t in tickets]


async def _run_triage(tickets: list[Ticket], model: str | None, concurrency: int) -> list[Triage]:
    async with AsyncTypeSafeClient(model=model) as client:
        return await Triager(client, concurrency).triage_all(tickets)


def _triages(args: argparse.Namespace, tickets: list[Ticket]) -> list[Triage]:
    if args.cache and Path(args.cache).exists() and not args.refresh:
        return [Triage(**raw) for raw in json.loads(Path(args.cache).read_text())]
    triages = asyncio.run(_run_triage(tickets, args.model, args.concurrency))
    if args.cache:
        Path(args.cache).parent.mkdir(parents=True, exist_ok=True)
        Path(args.cache).write_text(json.dumps([asdict(t) for t in triages], indent=2))
    return triages


def _write(text: str, out: str | None) -> None:
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text)
        print(f"wrote {out}", file=sys.stderr)
    else:
        print(text)


def cmd_triage(args: argparse.Namespace) -> None:
    tickets = _with_assignments(load_tickets(args.tickets))
    by_id = {t.ticket_id: t for t in _triages(args, tickets)}
    header = f"{'ticket':<8} {'pri':<4} {'route':<22} {'conf':>5} {'blocked':>7} {'eng':>5} {'ms':>6}  actions"
    print(header)
    print("-" * len(header))
    for ticket in tickets:
        tr = by_id[ticket.id]
        d = decide(tr, ticket)
        print(
            f"{ticket.id:<8} {d.priority:<4} {d.route:<22} {tr.queue_confidence:>5.2f} {tr.blocked:>7.2f} "
            f"{tr.needs_engineering:>5.2f} {tr.latency_ms:>6.0f}  {', '.join(d.actions)}"
        )


def cmd_handoff(args: argparse.Namespace) -> None:
    tickets = _with_assignments(load_tickets(args.tickets))
    by_id = {t.ticket_id: t for t in _triages(args, tickets)}
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(timezone.utc)
    rows = [Row(t, by_id[t.id], decide(by_id[t.id], t)) for t in tickets]
    _write(render_handoff(rows, now=now, shift=args.shift, thresholds=DEFAULT_THRESHOLDS), args.out)


def cmd_eval(args: argparse.Namespace) -> None:
    tickets = load_tickets(args.tickets)
    triages = _triages(args, tickets)
    model = triages[0].model if triages else "unknown"
    _write(render_report(evaluate(tickets, triages), model), args.out)


def cmd_doctor(args: argparse.Namespace) -> None:
    raw = json.loads(Path(args.file).read_text())
    body = raw.get("request", raw) if isinstance(raw, dict) else raw
    findings = check_request(body)
    if isinstance(raw, dict) and isinstance(raw.get("headers"), dict):
        findings += check_headers(raw["headers"])
    for f in findings:
        print(f"[{f.level.upper():7}] {f.path or '<body>'}: {f.message}")
    if not findings:
        print("No problems found in the request.")
    response = raw.get("response") if isinstance(raw, dict) else None
    if isinstance(response, dict) and "status" in response:
        print(f"\nHTTP {response['status']}: {explain_status(int(response['status']))}")
        if response.get("body") is not None:
            print(f"Server said: {json.dumps(response['body'])}")
    if isinstance(body, dict):
        print("\nReproduce with your own key:\n")
        print(repro_curl(body))
    if any(f.level == "error" for f in findings):
        sys.exit(1)


def cmd_models(args: argparse.Namespace) -> None:
    with TypeSafeClient() as client:
        for m in client.models.list().models:
            print(f"{m.name:<16} {m.release_date}  {m.description}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jev-desk", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def jev_command(name: str, help_text: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("tickets", help="JSONL file of tickets")
        p.add_argument("--model", default=None, help="Jev model (default: TYPESAFE_DEFAULT_MODEL or jev-latest)")
        p.add_argument("--cache", default="out/triage.json", help="Where to store/reuse triage results")
        p.add_argument("--refresh", action="store_true", help="Ignore the cache and call Jev again")
        p.add_argument("--concurrency", type=int, default=8)
        return p

    jev_command("triage", "Triage every ticket with one Jev request each").set_defaults(func=cmd_triage)

    handoff = jev_command("handoff", "Write the end-of-shift handoff")
    handoff.add_argument("--shift", default="US → EU")
    handoff.add_argument("--now", default=None, help="ISO timestamp to treat as 'now'")
    handoff.add_argument("--out", default=None)
    handoff.set_defaults(func=cmd_handoff)

    ev = jev_command("eval", "Evaluate triage against labeled tickets")
    ev.add_argument("--out", default=None)
    ev.set_defaults(func=cmd_eval)

    doctor = sub.add_parser("doctor", help="Check a customer's request/error offline and print a repro")
    doctor.add_argument("file", help="JSON: a request body, or {request, headers, response: {status, body}}")
    doctor.set_defaults(func=cmd_doctor)

    sub.add_parser("models", help="List models your key can use (connectivity check)").set_defaults(func=cmd_models)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except TypeSafeError as error:
        print(f"TypeSafe error: {error}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
