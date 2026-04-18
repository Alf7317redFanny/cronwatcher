"""CLI helpers for displaying job status trends."""
from __future__ import annotations
import argparse
from typing import List
from cronwatcher.job_status_history import StatusHistoryAnalyzer, StatusTrend


def add_status_history_args(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("trends", help="Show job status trends")
    p.add_argument("--job", metavar="NAME", help="Filter to a specific job")
    p.add_argument("--window", type=int, default=10, help="Recent runs to consider")
    p.set_defaults(cmd="trends")


def _bar(recent: List[str], width: int = 10) -> str:
    symbols = {"ok": "▓", "fail": "░"}
    padded = recent[-width:]
    return "".join(symbols.get(s, "?") for s in padded)


def run_trends_cmd(args: argparse.Namespace, analyzer: StatusHistoryAnalyzer, job_names: List[str]) -> int:
    names = [args.job] if getattr(args, "job", None) else job_names
    trends = analyzer.analyze_all(names)
    if not trends:
        print("No jobs found.")
        return 0
    print(f"{'Job':<25} {'Runs':>6} {'Fails':>6} {'Rate':>7}  {'Recent':<12}")
    print("-" * 65)
    for name, t in sorted(trends.items()):
        bar = _bar(t.recent)
        print(f"{name:<25} {t.total_runs:>6} {t.total_failures:>6} {t.success_rate:>6.1f}%  {bar}")
    return 0
