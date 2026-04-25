"""Track and report per-job uptime (availability) over a rolling window."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from cronwatcher.history import History, RunRecord


@dataclass
class UptimeResult:
    job_name: str
    total_runs: int
    successful_runs: int
    uptime_pct: float
    window_days: int
    since: datetime

    def __repr__(self) -> str:
        return (
            f"<UptimeResult job={self.job_name!r} "
            f"uptime={self.uptime_pct:.1f}% "
            f"runs={self.total_runs} window={self.window_days}d>"
        )

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "uptime_pct": round(self.uptime_pct, 4),
            "window_days": self.window_days,
            "since": self.since.isoformat(),
        }


class UptimeAnalyzer:
    """Compute uptime statistics for jobs from run history."""

    def __init__(self, history: History, window_days: int = 30) -> None:
        if window_days < 1:
            raise ValueError("window_days must be >= 1")
        self.history = history
        self.window_days = window_days

    def analyze(self, job_name: str) -> UptimeResult:
        since = datetime.utcnow() - timedelta(days=self.window_days)
        records: List[RunRecord] = [
            r for r in self.history.records
            if r.job_name == job_name and r.started_at >= since
        ]
        total = len(records)
        successful = sum(1 for r in records if r.success)
        pct = (successful / total * 100.0) if total > 0 else 0.0
        return UptimeResult(
            job_name=job_name,
            total_runs=total,
            successful_runs=successful,
            uptime_pct=pct,
            window_days=self.window_days,
            since=since,
        )

    def analyze_all(self, job_names: List[str]) -> List[UptimeResult]:
        return [self.analyze(name) for name in job_names]
