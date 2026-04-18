from __future__ import annotations
import argparse
from pathlib import Path
from cronwatcher.job_pause import PauseIndex

_DEFAULT_STATE = Path(".cronwatcher_pause.json")


def add_pause_args(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("pause", help="Pause or resume a cron job")
    sub = p.add_subparsers(dest="pause_action", required=True)

    pa = sub.add_parser("add", help="Pause a job")
    pa.add_argument("job", help="Job name")
    pa.add_argument("--reason", default="", help="Reason for pausing")
    pa.add_argument("--state-file", default=str(_DEFAULT_STATE))

    pr = sub.add_parser("remove", help="Resume a paused job")
    pr.add_argument("job", help="Job name")
    pr.add_argument("--state-file", default=str(_DEFAULT_STATE))

    pl = sub.add_parser("list", help="List paused jobs")
    pl.add_argument("--state-file", default=str(_DEFAULT_STATE))


def run_pause_cmd(args: argparse.Namespace) -> int:
    index = PauseIndex(Path(args.state_file))
    action = args.pause_action

    if action == "add":
        record = index.pause(args.job, reason=args.reason)
        print(f"Paused: {record}")
        return 0

    if action == "remove":
        removed = index.resume(args.job)
        if removed:
            print(f"Resumed job: {args.job}")
        else:
            print(f"Job not paused: {args.job}")
        return 0

    if action == "list":
        records = index.all_paused()
        if not records:
            print("No jobs are currently paused.")
        for r in records:
            reason = f" — {r.reason}" if r.reason else ""
            print(f"  {r.job_name}{reason}")
        return 0

    return 1
