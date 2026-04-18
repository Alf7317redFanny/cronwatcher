"""Tracks per-job status trends over recent runs."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
from cronwatcher.history import History, RunRecord


@dataclass
class StatusTrend:
    job_name: str
    recent: List[str] = field(default_factory=list)  # 'ok' | 'fail'
    total_runs: int = 0
    total_failures: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return round((self.total_runs - self.total_failures) / self.total_runs * 100, 1)

    @property
    def last_status(self) -> str | None:
        return self.recent[-1] if self.recent else None

    def __repr__(self) -> str:
        return (
            f"StatusTrend(job={self.job_name!r}, runs={self.total_runs}, "
            f"failures={self.total_failures}, rate={self.success_rate}%)"
        )


class StatusHistoryAnalyzer:
    def __init__(self, history: History, window: int = 10) -> None:
        self._history = history
        self._window = window

    def analyze(self, job_name: str) -> StatusTrend:
        records: List[RunRecord] = [
            r for r in self._history.records if r.job_name == job_name
        ]
        records.sort(key=lambda r: r.ran_at)
        recent = records[-self._window :]
        trend = StatusTrend(job_name=job_name)
        trend.total_runs = len(records)
        trend.total_failures = sum(1 for r in records if not r.success)
        trend.recent = ["ok" if r.success else "fail" for r in recent]
        return trend

    def analyze_all(self, job_names: List[str]) -> Dict[str, StatusTrend]:
        return {name: self.analyze(name) for name in job_names}
