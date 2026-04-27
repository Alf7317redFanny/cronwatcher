"""Detect schedule drift — when jobs consistently run late or early relative to
their expected schedule window."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from cronwatcher.history import History, RunRecord


@dataclass
class DriftSample:
    """A single observation of how far a run deviated from its scheduled time."""

    job_name: str
    scheduled_at: datetime
    actual_at: datetime
    delta_seconds: float  # positive = late, negative = early

    def __repr__(self) -> str:  # pragma: no cover
        direction = "late" if self.delta_seconds >= 0 else "early"
        return (
            f"<DriftSample job={self.job_name!r} "
            f"delta={abs(self.delta_seconds):.1f}s {direction}>"
        )


@dataclass
class DriftResult:
    """Aggregated drift statistics for a single job."""

    job_name: str
    sample_count: int
    mean_delta_seconds: float
    stddev_seconds: float
    max_late_seconds: float
    max_early_seconds: float  # stored as positive magnitude
    samples: List[DriftSample] = field(default_factory=list)

    @property
    def is_drifting(self) -> bool:
        """True when the mean absolute drift exceeds 60 seconds."""
        return abs(self.mean_delta_seconds) > 60

    def summary(self) -> str:
        direction = "late" if self.mean_delta_seconds >= 0 else "early"
        return (
            f"{self.job_name}: avg {abs(self.mean_delta_seconds):.0f}s {direction} "
            f"over {self.sample_count} run(s) "
            f"(stddev={self.stddev_seconds:.1f}s)"
        )

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "sample_count": self.sample_count,
            "mean_delta_seconds": round(self.mean_delta_seconds, 3),
            "stddev_seconds": round(self.stddev_seconds, 3),
            "max_late_seconds": round(self.max_late_seconds, 3),
            "max_early_seconds": round(self.max_early_seconds, 3),
            "is_drifting": self.is_drifting,
        }


class DriftAnalyzer:
    """Computes schedule drift for jobs by comparing actual run times against
    the timestamps stored in history records.

    Each ``RunRecord`` already carries a ``started_at`` timestamp.  When the
    config also provides a ``scheduled_at`` field we can compute the exact
    delta; otherwise we estimate drift from the inter-run intervals.
    """

    def __init__(self, history: History) -> None:
        self._history = history

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, job_name: str, window: int = 50) -> Optional[DriftResult]:
        """Return drift statistics for *job_name* using the last *window* runs.

        Returns ``None`` when there are fewer than two records (not enough data
        to establish a baseline interval).
        """
        records = [
            r
            for r in self._history.records
            if r.job_name == job_name and r.started_at is not None
        ]
        records = sorted(records, key=lambda r: r.started_at)[-window:]

        if len(records) < 2:
            return None

        samples = self._build_samples(records)
        if not samples:
            return None

        deltas = [s.delta_seconds for s in samples]
        mean = statistics.mean(deltas)
        stddev = statistics.pstdev(deltas)
        max_late = max((d for d in deltas if d >= 0), default=0.0)
        max_early = abs(min((d for d in deltas if d < 0), default=0.0))

        return DriftResult(
            job_name=job_name,
            sample_count=len(samples),
            mean_delta_seconds=mean,
            stddev_seconds=stddev,
            max_late_seconds=max_late,
            max_early_seconds=max_early,
            samples=samples,
        )

    def analyze_all(self, window: int = 50) -> Dict[str, DriftResult]:
        """Analyze drift for every job that appears in the history."""
        job_names = {r.job_name for r in self._history.records}
        results: Dict[str, DriftResult] = {}
        for name in sorted(job_names):
            result = self.analyze(name, window=window)
            if result is not None:
                results[name] = result
        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_samples(self, records: List[RunRecord]) -> List[DriftSample]:
        """Estimate drift by treating the *first* record's start time as the
        baseline and computing expected times from the median inter-run interval.
        """
        samples: List[DriftSample] = []

        # Compute inter-run intervals (seconds) to estimate the cadence.
        intervals = [
            (records[i].started_at - records[i - 1].started_at).total_seconds()
            for i in range(1, len(records))
            if records[i].started_at and records[i - 1].started_at
        ]
        if not intervals:
            return samples

        median_interval = statistics.median(intervals)
        if median_interval <= 0:
            return samples

        baseline = records[0].started_at
        for i, record in enumerate(records):
            expected = datetime.fromtimestamp(
                baseline.timestamp() + i * median_interval, tz=timezone.utc
            )
            actual = record.started_at.replace(tzinfo=timezone.utc) if record.started_at.tzinfo is None else record.started_at
            delta = (actual - expected).total_seconds()
            samples.append(
                DriftSample(
                    job_name=record.job_name,
                    scheduled_at=expected,
                    actual_at=actual,
                    delta_seconds=delta,
                )
            )

        return samples
