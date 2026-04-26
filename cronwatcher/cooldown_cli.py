"""CLI helpers for job cooldown management."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from cronwatcher.job_cooldown import CooldownManager, CooldownPolicy


def add_cooldown_args(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("cooldown", help="inspect or reset job cooldown state")
    sub = p.add_subparsers(dest="cooldown_action", required=True)

    status_p = sub.add_parser("status", help="show cooldown status for a job")
    status_p.add_argument("job", help="job name")
    status_p.add_argument("--state-file", default=".cronwatcher/cooldown.json")
    status_p.add_argument("--default-seconds", type=int, default=60)

    reset_p = sub.add_parser("reset", help="clear cooldown state for a job")
    reset_p.add_argument("job", help="job name")
    reset_p.add_argument("--state-file", default=".cronwatcher/cooldown.json")
    reset_p.add_argument("--default-seconds", type=int, default=60)


def _build_manager(args: argparse.Namespace) -> CooldownManager:
    """Construct a CooldownManager from parsed CLI arguments."""
    policy = CooldownPolicy(default_seconds=args.default_seconds)
    return CooldownManager(policy=policy, state_file=Path(args.state_file))


def run_cooldown_cmd(args: argparse.Namespace) -> int:
    """Dispatch a cooldown subcommand and return an exit code."""
    manager = _build_manager(args)

    if args.cooldown_action == "status":
        cooling = manager.is_cooling_down(args.job)
        remaining = manager.remaining_seconds(args.job)
        if cooling:
            print(f"{args.job}: cooling down — {remaining:.1f}s remaining")
        else:
            print(f"{args.job}: ready (no active cooldown)")
        return 0

    if args.cooldown_action == "reset":
        # Record a run far in the past so the cooldown is immediately expired.
        manager.record_run(args.job, when=datetime(2000, 1, 1))
        print(f"{args.job}: cooldown reset")
        return 0

    return 1
