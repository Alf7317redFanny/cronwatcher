"""CLI helpers for inspecting registered job callbacks."""
from __future__ import annotations

import argparse
from typing import Sequence

from cronwatcher.job_callbacks import CallbackRegistry


_EVENTS = ("on_start", "on_success", "on_failure")


def add_callbacks_args(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    """Attach *callbacks* sub-command to an existing subparser group."""
    p: argparse.ArgumentParser = subparsers.add_parser(
        "callbacks",
        help="Show registered lifecycle callbacks.",
    )
    p.add_argument(
        "--event",
        choices=_EVENTS,
        default=None,
        help="Filter to a specific event (default: show all).",
    )
    p.set_defaults(func=run_callbacks_cmd)


def run_callbacks_cmd(
    args: argparse.Namespace,
    registry: CallbackRegistry,
    *,
    out=None,
) -> int:
    """Print callback counts to *out* (defaults to stdout)."""
    import sys

    out = out or sys.stdout

    events = [args.event] if args.event else list(_EVENTS)
    total = 0
    for event in events:
        count = registry.count(event)
        total += count
        out.write(f"{event}: {count} callback(s)\n")

    out.write(f"Total: {total}\n")
    return 0


def callbacks_summary(registry: CallbackRegistry) -> str:
    """Return a one-line summary string of all registered callbacks."""
    parts = [f"{e}={registry.count(e)}" for e in _EVENTS]
    return "callbacks(" + ", ".join(parts) + ")"
