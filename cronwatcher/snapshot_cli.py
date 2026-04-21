"""CLI sub-commands for job snapshots."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from cronwatcher.job_snapshots import JobSnapshot, SnapshotStore


def add_snapshot_args(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("snapshot", help="Manage job state snapshots")
    ss = p.add_subparsers(dest="snapshot_action", required=True)

    # snapshot take <job>
    take = ss.add_parser("take", help="Record a snapshot for a job")
    take.add_argument("job", help="Job name")
    take.add_argument("--last-run", type=float, default=None, metavar="TS")
    take.add_argument("--last-status", choices=["ok", "failed"], default=None)
    take.add_argument("--run-count", type=int, default=0)
    take.add_argument("--failure-count", type=int, default=0)
    take.add_argument("--store", default=".cronwatcher/snapshots.json", metavar="FILE")

    # snapshot show <job>
    show = ss.add_parser("show", help="Show the latest snapshot for a job")
    show.add_argument("job", help="Job name")
    show.add_argument("--store", default=".cronwatcher/snapshots.json", metavar="FILE")

    # snapshot diff <job>
    diff = ss.add_parser("diff", help="Diff the last two snapshots for a job")
    diff.add_argument("job", help="Job name")
    diff.add_argument("--store", default=".cronwatcher/snapshots.json", metavar="FILE")


def run_snapshot_cmd(args: argparse.Namespace) -> int:
    store = SnapshotStore(Path(args.store))

    if args.snapshot_action == "take":
        snap = JobSnapshot(
            job_name=args.job,
            timestamp=time.time(),
            last_run=args.last_run,
            last_status=args.last_status,
            run_count=args.run_count,
            failure_count=args.failure_count,
        )
        store.record(snap)
        print(f"Snapshot recorded for {args.job!r}")
        return 0

    if args.snapshot_action == "show":
        snap = store.latest_for(args.job)
        if snap is None:
            print(f"No snapshots found for {args.job!r}")
            return 1
        for k, v in snap.to_dict().items():
            print(f"  {k}: {v}")
        return 0

    if args.snapshot_action == "diff":
        changes = store.diff(args.job)
        if changes is None:
            print(f"Not enough snapshots to diff for {args.job!r}")
            return 1
        for field, delta in changes.items():
            print(f"  {field}: {delta['before']!r} -> {delta['after']!r}")
        return 0

    return 1
