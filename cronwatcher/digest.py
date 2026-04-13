"""Periodic digest report builder for cronwatcher."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from cronwatcher.history import History, RunRecord
from cronwatcher.scheduler import Scheduler


@dataclass
class DigestEntry:
    job_name: str
    total_runs: int
    failures: int
    last_run: Optional[datetime]
    success_rate: float

    def __repr__(self) -> str:
        return (
            f"DigestEntry(job={self.job_name!r}, runs={self.total_runs}, "
            f"failures={self.failures}, success_rate={self.success_rate:.1%})"
        )


class DigestBuilder:
    """Builds a summary digest of job performance over a time window."""

    def __init__(self, history: History, scheduler: Scheduler):
        self.history = history
        self.scheduler = scheduler

    def build(self, since: Optional[datetime] = None) -> List[DigestEntry]:
        """Return one DigestEntry per tracked job."""
        entries = []
        for job_name in self.scheduler.statuses:
            records = self._records_for(job_name, since)
            total = len(records)
            failures = sum(1 for r in records if not r.success)
            last_run = max((r.ran_at for r in records), default=None)
            rate = ((total - failures) / total) if total > 0 else 0.0
            entries.append(
                DigestEntry(
                    job_name=job_name,
                    total_runs=total,
                    failures=failures,
                    last_run=last_run,
                    success_rate=rate,
                )
            )
        return entries

    def format_text(self, since: Optional[datetime] = None) -> str:
        """Render a human-readable digest string."""
        entries = self.build(since)
        lines = ["=== CronWatcher Digest ==="]
        for e in entries:
            last = e.last_run.strftime("%Y-%m-%d %H:%M") if e.last_run else "never"
            lines.append(
                f"  {e.job_name}: {e.total_runs} runs, "
                f"{e.failures} failures, "
                f"{e.success_rate:.0%} success, last={last}"
            )
        if not entries:
            lines.append("  No jobs tracked.")
        return "\n".join(lines)

    def _records_for(self, job_name: str, since: Optional[datetime]) -> List[RunRecord]:
        records = [r for r in self.history.records if r.job_name == job_name]
        if since:
            records = [r for r in records if r.ran_at >= since]
        return records
