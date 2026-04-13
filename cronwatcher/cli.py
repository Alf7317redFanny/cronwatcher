"""CLI entry point for cronwatcher."""

import argparse
import sys
from pathlib import Path

from cronwatcher.config import load
from cronwatcher.history import History
from cronwatcher.monitor import Monitor
from cronwatcher.notifier import Notifier, NotifierConfig
from cronwatcher.runner import JobRunner
from cronwatcher.scheduler import Scheduler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatcher",
        description="Monitor cron job execution and alert on failures or missed runs.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("cronwatcher.json"),
        help="Path to the config file (default: cronwatcher.json)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("run", help="Run all configured jobs and check for missed runs")
    subparsers.add_parser("check", help="Check for missed runs without running jobs")

    history_parser = subparsers.add_parser("history", help="Show run history")
    history_parser.add_argument("--job", type=str, default=None, help="Filter by job name")
    history_parser.add_argument("--limit", type=int, default=20, help="Max records to show")

    return parser


def cmd_run(config_path: Path) -> int:
    watcher_config = load(config_path)
    scheduler = Scheduler(watcher_config.jobs)
    history = History(watcher_config.history_path)
    notifier_cfg = NotifierConfig(**watcher_config.notifier) if watcher_config.notifier else None
    notifier = Notifier(notifier_cfg) if notifier_cfg else None
    runner = JobRunner(scheduler, history, notifier)
    monitor = Monitor(scheduler, notifier)

    for job in watcher_config.jobs:
        runner.run_job(job)

    missed = monitor.check_missed_runs()
    if missed:
        print(f"[cronwatcher] {len(missed)} missed run(s) detected.")
    return 0


def cmd_check(config_path: Path) -> int:
    watcher_config = load(config_path)
    scheduler = Scheduler(watcher_config.jobs)
    notifier_cfg = NotifierConfig(**watcher_config.notifier) if watcher_config.notifier else None
    notifier = Notifier(notifier_cfg) if notifier_cfg else None
    monitor = Monitor(scheduler, notifier)

    missed = monitor.check_missed_runs()
    if not missed:
        print("[cronwatcher] All jobs on schedule.")
    else:
        for m in missed:
            print(f"  MISSED: {m}")
    return 0


def cmd_history(config_path: Path, job_name: str | None, limit: int) -> int:
    watcher_config = load(config_path)
    history = History(watcher_config.history_path)
    records = history.get_recent(job_name=job_name, limit=limit)
    if not records:
        print("[cronwatcher] No history found.")
        return 0
    for record in records:
        print(record)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.config.exists():
        print(f"[cronwatcher] Config file not found: {args.config}", file=sys.stderr)
        return 1

    if args.command == "run":
        return cmd_run(args.config)
    elif args.command == "check":
        return cmd_check(args.config)
    elif args.command == "history":
        return cmd_history(args.config, args.job, args.limit)

    return 0


if __name__ == "__main__":
    sys.exit(main())
