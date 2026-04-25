"""CLI helpers for the job uptime feature."""
from __future__ import annotations

import argparse
from typing import List

from cronwatcher.job_uptime import UptimeAnalyzer, UptimeResult


def add_uptime_args(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("uptime", help="Show per-job uptime statistics")
    p.add_argument(
        "--window",
        type=int,
        default=30,
        metavar="DAYS",
        help="Rolling window in days (default: 30)",
    )
    p.add_argument(
        "--job",
        dest="job_names",
        action="append",
        default=[],
        metavar="NAME",
        help="Filter to specific job(s); repeatable",
    )
    p.add_argument(
        "--min-uptime",
        type=float,
        default=0.0,
        metavar="PCT",
        help="Only show jobs below this uptime %% (0 = show all)",
    )


def run_uptime_cmd(args: argparse.Namespace, analyzer: UptimeAnalyzer, all_jobs: List[str]) -> int:
    job_names = args.job_names if args.job_names else all_jobs
    results = analyzer.analyze_all(job_names)

    if args.min_uptime > 0:
        results = [r for r in results if r.uptime_pct < args.min_uptime]

    if not results:
        print("No uptime data found.")
        return 0

    header = f"{'Job':<30} {'Runs':>6} {'OK':>6} {'Uptime':>8}  Window"
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r.job_name:<30} {r.total_runs:>6} {r.successful_runs:>6} "
            f"{r.uptime_pct:>7.1f}%  {r.window_days}d"
        )
    return 0


def uptime_summary(results: List[UptimeResult]) -> str:
    if not results:
        return "No uptime data."
    lines = [f"{r.job_name}: {r.uptime_pct:.1f}% ({r.total_runs} runs)" for r in results]
    return "\n".join(lines)
