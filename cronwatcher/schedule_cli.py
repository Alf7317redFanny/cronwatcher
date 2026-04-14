"""CLI helpers for inspecting cron schedules."""
from __future__ import annotations

import argparse
from typing import Optional

from cronwatcher.job_schedule import is_valid, schedule_info, describe


def add_schedule_args(parser: argparse.ArgumentParser) -> None:
    """Attach schedule-inspection sub-commands to *parser*."""
    sub = parser.add_subparsers(dest="schedule_cmd")

    validate_p = sub.add_parser("validate", help="Check if a cron expression is valid")
    validate_p.add_argument("expression", help="Cron expression or preset (e.g. @daily)")

    describe_p = sub.add_parser("describe", help="Human-readable description of a schedule")
    describe_p.add_argument("expression", help="Cron expression or preset")

    next_p = sub.add_parser("next", help="Show next and previous run times")
    next_p.add_argument("expression", help="Cron expression or preset")
    next_p.add_argument(
        "--count",
        type=int,
        default=3,
        help="Number of upcoming runs to display (default: 3)",
    )


def run_schedule_cmd(args: argparse.Namespace) -> Optional[int]:
    """Dispatch to the appropriate schedule sub-command handler.

    Returns an exit code (0 = success, non-zero = error).
    """
    cmd = getattr(args, "schedule_cmd", None)

    if cmd == "validate":
        if is_valid(args.expression):
            print(f"✓ '{args.expression}' is a valid cron expression.")
            return 0
        else:
            print(f"✗ '{args.expression}' is NOT a valid cron expression.")
            return 1

    if cmd == "describe":
        if not is_valid(args.expression):
            print(f"Error: '{args.expression}' is not a valid cron expression.")
            return 1
        print(describe(args.expression))
        return 0

    if cmd == "next":
        if not is_valid(args.expression):
            print(f"Error: '{args.expression}' is not a valid cron expression.")
            return 1
        from croniter import croniter
        from datetime import datetime
        from cronwatcher.job_schedule import normalize

        norm = normalize(args.expression)
        cron = croniter(norm, datetime.utcnow())
        print(f"Schedule : {describe(args.expression)}")
        print(f"Expression: {norm}")
        print("Upcoming runs (UTC):")
        for _ in range(args.count):
            print(f"  {cron.get_next(datetime).isoformat()}")  # type: ignore[arg-type]
        return 0

    return None  # no sub-command matched
