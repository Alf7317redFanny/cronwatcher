"""CLI commands for managing per-job notification preferences."""
from __future__ import annotations
import argparse
from cronwatcher.job_notifications import NotificationIndex, NotificationPrefs, VALID_CHANNELS


def add_notifications_args(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("notifications", help="manage per-job notification prefs")
    sub = p.add_subparsers(dest="notif_action")

    s = sub.add_parser("set", help="set notification preferences for a job")
    s.add_argument("job", help="job name")
    s.add_argument("--channels", nargs="+", default=["log"], choices=sorted(VALID_CHANNELS))
    s.add_argument("--on-failure", action=argparse.BooleanOptionalAction, default=True)
    s.add_argument("--on-missed", action=argparse.BooleanOptionalAction, default=True)
    s.add_argument("--on-recovery", action=argparse.BooleanOptionalAction, default=False)
    s.add_argument("--state-file", default="notif_prefs.json")

    g = sub.add_parser("get", help="show notification preferences for a job")
    g.add_argument("job", help="job name")
    g.add_argument("--state-file", default="notif_prefs.json")

    ls = sub.add_parser("list", help="list all notification preferences")
    ls.add_argument("--state-file", default="notif_prefs.json")


def run_notifications_cmd(args: argparse.Namespace) -> int:
    index = NotificationIndex(state_file=getattr(args, "state_file", "notif_prefs.json"))

    if args.notif_action == "set":
        prefs = NotificationPrefs(
            channels=args.channels,
            on_failure=args.on_failure,
            on_missed=args.on_missed,
            on_recovery=args.on_recovery,
        )
        index.set(args.job, prefs)
        print(f"Notification prefs updated for job '{args.job}'.")
        return 0

    if args.notif_action == "get":
        prefs = index.get(args.job)
        print(f"Job: {args.job}")
        print(f"  channels   : {', '.join(prefs.channels)}")
        print(f"  on_failure : {prefs.on_failure}")
        print(f"  on_missed  : {prefs.on_missed}")
        print(f"  on_recovery: {prefs.on_recovery}")
        return 0

    if args.notif_action == "list":
        all_prefs = index.all()
        if not all_prefs:
            print("No notification preferences configured.")
            return 0
        for job, prefs in sorted(all_prefs.items()):
            print(f"{job}: channels={prefs.channels} failure={prefs.on_failure} "
                  f"missed={prefs.on_missed} recovery={prefs.on_recovery}")
        return 0

    print("No action specified. Use --help.")
    return 1
