"""CLI helpers for the job forecast feature."""
from __future__ import annotations

import argparse
from datetime import datetime
from typing import List, Optional

from cronwatcher.config import JobConfig
from cronwatcher.job_forecast import ForecastEntry, JobForecaster


def add_forecast_args(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser("forecast", help="Show upcoming scheduled run times")
    p.add_argument(
        "--count",
        type=int,
        default=5,
        metavar="N",
        help="Number of future runs to show per job (default: 5)",
    )
    p.add_argument(
        "--job",
        metavar="NAME",
        default=None,
        help="Limit output to a single job name",
    )
    p.set_defaults(func=run_forecast_cmd)


def run_forecast_cmd(args: argparse.Namespace, jobs: List[JobConfig]) -> int:
    if args.job:
        jobs = [j for j in jobs if j.name == args.job]
        if not jobs:
            print(f"No job named {args.job!r} found.")
            return 1

    forecaster = JobForecaster(jobs, count=args.count)
    entries = forecaster.forecast()
    _print_forecast(entries)
    return 0


def _print_forecast(entries: List[ForecastEntry]) -> None:
    for entry in entries:
        print(f"\n{entry.job_name}")
        if not entry.next_runs:
            print("  (unable to compute schedule)")
            continue
        for dt in entry.next_runs:
            print(f"  {dt.strftime('%Y-%m-%d %H:%M UTC')}")


def forecast_summary(entries: List[ForecastEntry], now: Optional[datetime] = None) -> str:
    """Return a compact one-line summary of the soonest upcoming run across all jobs."""
    now = now or datetime.utcnow()
    soonest: Optional[tuple] = None
    for entry in entries:
        if entry.next_runs:
            t = entry.next_runs[0]
            if soonest is None or t < soonest[1]:
                soonest = (entry.job_name, t)
    if soonest is None:
        return "No upcoming runs found."
    delta = int((soonest[1] - now).total_seconds() // 60)
    return f"Next run: {soonest[0]} in ~{delta} min ({soonest[1].strftime('%H:%M UTC')})"
