"""CLI helpers for job filtering — shared by `run`, `check`, and `history` commands."""

from __future__ import annotations

import argparse
from typing import List, Optional

from cronwatcher.config import JobConfig
from cronwatcher.job_filter import FilterCriteria, JobFilter
from cronwatcher.scheduler import Scheduler


def add_filter_args(parser: argparse.ArgumentParser) -> None:
    """Attach common filter flags to an existing sub-parser."""
    parser.add_argument(
        "--tag",
        dest="tags",
        metavar="TAG",
        action="append",
        default=[],
        help="Filter jobs by tag (repeatable).",
    )
    parser.add_argument(
        "--name",
        dest="name_contains",
        metavar="SUBSTR",
        default=None,
        help="Filter jobs whose name contains SUBSTR (case-insensitive).",
    )
    parser.add_argument(
        "--status",
        dest="status",
        choices=["ok", "failed", "unknown"],
        default=None,
        help="Filter jobs by last known status.",
    )


def criteria_from_args(args: argparse.Namespace) -> FilterCriteria:
    """Build a FilterCriteria from parsed CLI args."""
    return FilterCriteria(
        tags=getattr(args, "tags", []) or [],
        name_contains=getattr(args, "name_contains", None),
        status=getattr(args, "status", None),
    )


def filtered_jobs(
    args: argparse.Namespace,
    jobs: List[JobConfig],
    scheduler: Scheduler,
) -> List[JobConfig]:
    """Convenience wrapper used by CLI commands."""
    criteria = criteria_from_args(args)
    return JobFilter(jobs, scheduler).apply(criteria)
