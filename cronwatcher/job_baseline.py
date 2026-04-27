"""Baseline duration tracking for cron jobs.

Records the expected (baseline) runtime for each job based on historical
data and flags runs that deviate significantly from that baseline.
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class BaselineRecord:
    job_name: str
    mean_seconds: float
    stddev_seconds: float
    sample_count: int

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "mean_seconds": self.mean_seconds,
            "stddev_seconds": self.stddev_seconds,
            "sample_count": self.sample_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BaselineRecord":
        return cls(
            job_name=data["job_name"],
            mean_seconds=data["mean_seconds"],
            stddev_seconds=data["stddev_seconds"],
            sample_count=data["sample_count"],
        )

    def __repr__(self) -> str:
        return (
            f"BaselineRecord(job={self.job_name!r}, "
            f"mean={self.mean_seconds:.2f}s, stddev={self.stddev_seconds:.2f}s, "
            f"n={self.sample_count})"
        )


@dataclass
class DeviationResult:
    job_name: str
    duration_seconds: float
    baseline: BaselineRecord
    z_score: float
    is_anomaly: bool

    def __repr__(self) -> str:
        flag = "ANOMALY" if self.is_anomaly else "ok"
        return (
            f"DeviationResult(job={self.job_name!r}, "
            f"duration={self.duration_seconds:.2f}s, z={self.z_score:.2f}, {flag})"
        )


class BaselineIndex:
    """Persists and queries per-job duration baselines."""

    def __init__(self, state_file: Path, z_threshold: float = 2.5) -> None:
        self._path = state_file
        self.z_threshold = z_threshold
        self._records: Dict[str, BaselineRecord] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            raw = json.loads(self._path.read_text())
            self._records = {
                k: BaselineRecord.from_dict(v) for k, v in raw.items()
            }

    def _save(self) -> None:
        self._path.write_text(
            json.dumps({k: v.to_dict() for k, v in self._records.items()}, indent=2)
        )

    def update(self, job_name: str, durations: List[float]) -> Optional[BaselineRecord]:
        """Recompute baseline from a list of historical durations."""
        if len(durations) < 2:
            return None
        mean = statistics.mean(durations)
        stddev = statistics.stdev(durations)
        rec = BaselineRecord(
            job_name=job_name,
            mean_seconds=mean,
            stddev_seconds=stddev,
            sample_count=len(durations),
        )
        self._records[job_name] = rec
        self._save()
        return rec

    def get(self, job_name: str) -> Optional[BaselineRecord]:
        return self._records.get(job_name)

    def check_deviation(self, job_name: str, duration_seconds: float) -> Optional[DeviationResult]:
        """Return a DeviationResult if a baseline exists, else None."""
        rec = self._records.get(job_name)
        if rec is None:
            return None
        if rec.stddev_seconds == 0:
            z = 0.0
        else:
            z = abs(duration_seconds - rec.mean_seconds) / rec.stddev_seconds
        return DeviationResult(
            job_name=job_name,
            duration_seconds=duration_seconds,
            baseline=rec,
            z_score=z,
            is_anomaly=z > self.z_threshold,
        )

    def all_baselines(self) -> List[BaselineRecord]:
        return list(self._records.values())
