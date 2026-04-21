"""CLI sub-commands for viewing job metrics."""
from __future__ import annotations

import argparse
from pathlib import Path

from cronwatcher.job_metrics import MetricsStore


def add_metrics_args(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("metrics", help="Show job run metrics")
    p.add_argument("--state-file", default=".cronwatcher/metrics.json",
                   help="Path to metrics state file")
    p.add_argument("--job", default=None, help="Filter to a specific job name")
    p.set_defaults(func=run_metrics_cmd)


def run_metrics_cmd(args: argparse.Namespace) -> int:
    store = MetricsStore(Path(args.state_file))

    job_names = [args.job] if args.job else store.all_job_names()
    if not job_names:
        print("No metrics recorded yet.")
        return 0

    header = f"{'Job':<30} {'Runs':>5} {'OK':>5} {'Fail':>5} {'Avg(s)':>8} {'Min(s)':>8} {'Max(s)':>8}"
    print(header)
    print("-" * len(header))

    for name in job_names:
        summary = store.summarize(name)
        if summary is None:
            continue
        print(
            f"{summary.job_name:<30}"
            f" {summary.total_runs:>5}"
            f" {summary.successful_runs:>5}"
            f" {summary.failed_runs:>5}"
            f" {summary.avg_duration:>8.2f}"
            f" {summary.min_duration:>8.2f}"
            f" {summary.max_duration:>8.2f}"
        )
    return 0
