"""CLI commands for job heartbeat management."""

from __future__ import annotations

import argparse
from pathlib import Path

from cronwatcher.job_heartbeat import HeartbeatIndex


def add_heartbeat_args(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("heartbeat", help="manage job heartbeats")
    hb_sub = p.add_subparsers(dest="hb_action", required=True)

    ping = hb_sub.add_parser("ping", help="record a heartbeat for a job")
    ping.add_argument("job", help="job name")
    ping.add_argument("--interval", type=int, default=None, help="expected interval in seconds")
    ping.add_argument("--state-file", default="heartbeats.json")

    status = hb_sub.add_parser("status", help="show heartbeat status for all jobs")
    status.add_argument("--state-file", default="heartbeats.json")
    status.add_argument("--stale-only", action="store_true", help="only show stale jobs")


def run_heartbeat_cmd(args: argparse.Namespace) -> int:
    index = HeartbeatIndex(Path(args.state_file))

    if args.hb_action == "ping":
        rec = index.ping(args.job, interval_seconds=args.interval)
        print(f"Heartbeat recorded: {rec}")
        return 0

    if args.hb_action == "status":
        records = index.stale_jobs() if args.stale_only else index.all()
        if not records:
            print("No heartbeat records found.")
            return 0
        for rec in records:
            stale_marker = " [STALE]" if rec.is_stale() else ""
            print(f"  {rec.job_name}: last_seen={rec.last_seen.isoformat()}{stale_marker}")
        return 0

    return 1


def heartbeat_summary(index: HeartbeatIndex) -> str:
    total = len(index.all())
    stale = len(index.stale_jobs())
    return f"heartbeats: {total} tracked, {stale} stale"
