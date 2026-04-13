"""CLI helpers for priority-aware job filtering and display."""
from __future__ import annotations

import argparse
from typing import List, Optional, Sequence

from cronwatcher.config import JobConfig
from cronwatcher.job_priority import Priority, PriorityIndex


def add_priority_args(parser: argparse.ArgumentParser) -> None:
    """Attach --priority and --sort-priority flags to an argument parser."""
    parser.add_argument(
        "--priority",
        metavar="LEVEL",
        default=None,
        help="Filter jobs by priority level (LOW, NORMAL, HIGH, CRITICAL).",
    )
    parser.add_argument(
        "--sort-priority",
        action="store_true",
        default=False,
        help="Sort output by job priority (highest first).",
    )


def apply_priority_filter(
    jobs: Sequence[JobConfig],
    index: PriorityIndex,
    priority_str: Optional[str],
    sort: bool,
) -> List[JobConfig]:
    """Filter and/or sort jobs based on CLI priority arguments."""
    result = list(jobs)

    if priority_str is not None:
        level = Priority.from_str(priority_str)
        result = index.jobs_at(result, level)

    if sort:
        result = index.sorted_jobs(result)

    return result


def priority_label(index: PriorityIndex, job_name: str) -> str:
    """Return a short human-readable label for a job's priority."""
    p = index.get(job_name)
    symbols = {
        Priority.LOW: "↓ LOW",
        Priority.NORMAL: "  NORMAL",
        Priority.HIGH: "↑ HIGH",
        Priority.CRITICAL: "‼ CRITICAL",
    }
    return symbols.get(p, str(p))
