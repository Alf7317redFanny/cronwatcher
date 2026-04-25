"""CLI subcommands for inspecting and managing job run quotas."""
from __future__ import annotations

import argparse
from pathlib import Path

from cronwatcher.job_quota import QuotaManager, QuotaPolicy


def add_quota_args(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("quota", help="Inspect job run quotas")
    sub = p.add_subparsers(dest="quota_action", required=True)

    status_p = sub.add_parser("status", help="Show quota usage for a job")
    status_p.add_argument("job", help="Job name")
    status_p.add_argument("--state-file", default="quota_state.json")
    status_p.add_argument("--max-runs", type=int, default=0)
    status_p.add_argument("--window", type=int, default=3600, dest="window_seconds")

    reset_p = sub.add_parser("reset", help="Reset quota counters for a job")
    reset_p.add_argument("job", help="Job name")
    reset_p.add_argument("--state-file", default="quota_state.json")
    reset_p.add_argument("--max-runs", type=int, default=0)
    reset_p.add_argument("--window", type=int, default=3600, dest="window_seconds")


def run_quota_cmd(args: argparse.Namespace) -> int:
    policy = QuotaPolicy(
        max_runs=args.max_runs,
        window_seconds=args.window_seconds,
    )
    manager = QuotaManager(policy=policy, state_file=Path(args.state_file))

    if args.quota_action == "status":
        usage = manager.usage(args.job)
        limit = policy.limit_for(args.job)
        limit_str = str(limit) if limit > 0 else "unlimited"
        allowed = "yes" if manager.allowed(args.job) else "no"
        print(f"Job      : {args.job}")
        print(f"Usage    : {usage} / {limit_str}  (window: {args.window_seconds}s)")
        print(f"Allowed  : {allowed}")
        return 0

    if args.quota_action == "reset":
        state = manager._states.get(args.job)
        if state:
            state.timestamps.clear()
            manager._save()
        print(f"Quota reset for job '{args.job}'.")
        return 0

    return 1


def quota_summary(manager: QuotaManager, job_names: list) -> str:
    lines = []
    for name in job_names:
        usage = manager.usage(name)
        limit = manager.policy.limit_for(name)
        limit_str = str(limit) if limit > 0 else "∞"
        lines.append(f"{name}: {usage}/{limit_str}")
    return "\n".join(lines)
