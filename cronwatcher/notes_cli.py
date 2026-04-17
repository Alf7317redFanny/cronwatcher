"""CLI helpers for job notes."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
from cronwatcher.job_notes import NoteIndex


def add_notes_args(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("notes", help="manage job notes")
    p.add_argument("action", choices=["add", "list", "clear"], help="action to perform")
    p.add_argument("job", help="job name")
    p.add_argument("--text", default="", help="note text (required for add)")
    p.add_argument("--notes-file", default=".cronwatcher_notes.json", help="notes storage path")


def run_notes_cmd(args: argparse.Namespace) -> int:
    index = NoteIndex(Path(args.notes_file))

    if args.action == "add":
        if not args.text.strip():
            print("Error: --text is required for add")
            return 1
        ts = datetime.now(timezone.utc).isoformat()
        entry = index.add(args.job, args.text.strip(), ts)
        print(f"Note added: {entry}")
        return 0

    if args.action == "list":
        notes = index.get(args.job)
        if not notes:
            print(f"No notes for {args.job!r}")
            return 0
        for n in notes:
            print(f"[{n.timestamp}] {n.text}")
        return 0

    if args.action == "clear":
        removed = index.delete_all(args.job)
        print(f"Removed {removed} note(s) for {args.job!r}")
        return 0

    return 1
