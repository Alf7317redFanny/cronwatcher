"""CLI subcommands for managing job runbooks."""
from __future__ import annotations

import argparse
from pathlib import Path

from cronwatcher.job_runbook import RunbookIndex

_DEFAULT_STATE = Path("runbooks.json")


def add_runbook_args(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("runbook", help="Manage job runbooks")
    sub = p.add_subparsers(dest="runbook_action")

    s = sub.add_parser("set", help="Attach a runbook to a job")
    s.add_argument("job", help="Job name")
    s.add_argument("--url", default=None, help="Runbook URL")
    s.add_argument("--step", dest="steps", action="append", default=[], metavar="STEP", help="Remediation step (repeatable)")
    s.add_argument("--state-file", default=str(_DEFAULT_STATE))

    g = sub.add_parser("get", help="Show runbook for a job")
    g.add_argument("job", help="Job name")
    g.add_argument("--state-file", default=str(_DEFAULT_STATE))

    r = sub.add_parser("remove", help="Remove runbook for a job")
    r.add_argument("job", help="Job name")
    r.add_argument("--state-file", default=str(_DEFAULT_STATE))

    sub.add_parser("list", help="List all runbooks").add_argument("--state-file", default=str(_DEFAULT_STATE))


def run_runbook_cmd(args: argparse.Namespace) -> int:
    index = RunbookIndex(Path(args.state_file))
    action = getattr(args, "runbook_action", None)

    if action == "set":
        entry = index.set(args.job, url=args.url, steps=args.steps)
        print(f"Runbook set: {entry}")
        return 0

    if action == "get":
        entry = index.get(args.job)
        if entry is None:
            print(f"No runbook for {args.job!r}")
            return 1
        print(f"Job  : {entry.job_name}")
        print(f"URL  : {entry.url or '(none)'}")
        for i, step in enumerate(entry.steps, 1):
            print(f"  {i}. {step}")
        return 0

    if action == "remove":
        removed = index.remove(args.job)
        print("Removed." if removed else f"No runbook found for {args.job!r}.")
        return 0 if removed else 1

    if action == "list":
        entries = index.all()
        if not entries:
            print("No runbooks registered.")
            return 0
        for e in entries:
            print(e)
        return 0

    print("No runbook action specified.")
    return 1
