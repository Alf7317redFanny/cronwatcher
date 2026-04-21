"""Formats and emits a metrics report for a set of jobs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from cronwatcher.job_metrics import JobMetricsSummary, MetricsStore


@dataclass
class MetricsReport:
    summaries: List[JobMetricsSummary]

    def as_text(self) -> str:
        if not self.summaries:
            return "No metrics available."
        lines = [
            f"{'Job':<28} {'Runs':>5} {'OK':>5} {'Fail':>5} {'Avg':>8} {'Min':>8} {'Max':>8}",
            "-" * 72,
        ]
        for s in self.summaries:
            lines.append(
                f"{s.job_name:<28}"
                f" {s.total_runs:>5}"
                f" {s.successful_runs:>5}"
                f" {s.failed_runs:>5}"
                f" {s.avg_duration:>8.2f}"
                f" {s.min_duration:>8.2f}"
                f" {s.max_duration:>8.2f}"
            )
        return "\n".join(lines)

    def as_dict(self) -> dict:
        return {
            "summaries": [
                {
                    "job_name": s.job_name,
                    "total_runs": s.total_runs,
                    "successful_runs": s.successful_runs,
                    "failed_runs": s.failed_runs,
                    "avg_duration": round(s.avg_duration, 4),
                    "min_duration": round(s.min_duration, 4),
                    "max_duration": round(s.max_duration, 4),
                }
                for s in self.summaries
            ]
        }


class MetricsReporter:
    def __init__(self, store: MetricsStore) -> None:
        self._store = store

    def report(self, job_names: Optional[List[str]] = None) -> MetricsReport:
        names = job_names if job_names is not None else self._store.all_job_names()
        summaries = []
        for name in names:
            summary = self._store.summarize(name)
            if summary is not None:
                summaries.append(summary)
        return MetricsReport(summaries=summaries)
