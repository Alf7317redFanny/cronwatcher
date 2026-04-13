"""Retention policy for pruning old run history records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cronwatcher.history import History


@dataclass
class RetentionPolicy:
    """Defines how long run records should be kept."""

    max_age_days: int = 30
    max_records_per_job: int = 100

    def __post_init__(self) -> None:
        if self.max_age_days <= 0:
            raise ValueError("max_age_days must be a positive integer")
        if self.max_records_per_job <= 0:
            raise ValueError("max_records_per_job must be a positive integer")


class RetentionManager:
    """Applies a RetentionPolicy to a History instance, pruning stale records."""

    def __init__(self, history: "History", policy: RetentionPolicy) -> None:
        self.history = history
        self.policy = policy

    def prune(self) -> int:
        """Remove records that violate the retention policy.

        Returns the number of records removed.
        """
        cutoff = datetime.utcnow() - timedelta(days=self.policy.max_age_days)
        removed = 0

        # Group records by job name
        by_job: dict[str, list] = {}
        for record in self.history.records:
            by_job.setdefault(record.job_name, []).append(record)

        kept = []
        for job_name, records in by_job.items():
            # Sort newest first
            records.sort(key=lambda r: r.timestamp, reverse=True)

            # Apply age filter then cap by max_records_per_job
            fresh = [r for r in records if r.timestamp >= cutoff]
            capped = fresh[: self.policy.max_records_per_job]

            removed += len(records) - len(capped)
            kept.extend(capped)

        self.history.records = kept
        if removed:
            self.history.save()

        return removed
