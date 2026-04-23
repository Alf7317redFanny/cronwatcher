"""CLI helpers for inspecting and managing job concurrency slots."""
from __future__ import annotations

import argparse
from pathlib import Path

from cronwatcher.job_concurrency import ConcurrencyManager, ConcurrencyPolicy


def add_concurrency_args(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("concurrency", help="Manage job concurrency slots")
    sub = p.add_subparsers(dest="concurrency_action")

    ls = sub.add_parser("list", help="List active slots")
    ls.add_argument("--job", default=None, help="Filter by job name")
    ls.add_argument("--state-file", default=".cronwatcher/concurrency.json")

    rel = sub.add_parser("release", help="Release all slots for a job")
    rel.add_argument("job", help="Job name")
    rel.add_argument("--state-file", default=".cronwatcher/concurrency.json")


def run_concurrency_cmd(args: argparse.Namespace) -> int:
    policy = ConcurrencyPolicy()
    manager = ConcurrencyManager(policy, Path(args.state_file))

    if args.concurrency_action == "list":
        slots = manager.active_for(args.job) if args.job else manager._slots
        if not slots:
            print("No active concurrency slots.")
            return 0
        for slot in slots:
            print(f"  {slot.job_name:<30} pid={slot.pid}  started={slot.started_at}")
        return 0

    if args.concurrency_action == "release":
        count = manager.release_all(args.job)
        print(f"Released {count} slot(s) for '{args.job}'.")
        return 0

    print("No concurrency action specified. Use 'list' or 'release'.")
    return 1


def concurrency_summary(manager: ConcurrencyManager, job_name: str) -> str:
    slots = manager.active_for(job_name)
    if not slots:
        return f"{job_name}: no active slots"
    lines = [f"{job_name}: {len(slots)} active slot(s)"]
    for s in slots:
        lines.append(f"  pid={s.pid} started={s.started_at}")
    return "\n".join(lines)
