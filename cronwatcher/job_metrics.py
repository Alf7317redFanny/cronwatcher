"""Lightweight metrics collection for job runs (durations, counts)."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class MetricSample:
    job_name: str
    duration_seconds: float
    success: bool
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MetricSample":
        return cls(
            job_name=d["job_name"],
            duration_seconds=d["duration_seconds"],
            success=d["success"],
            timestamp=d["timestamp"],
        )

    def __repr__(self) -> str:
        status = "ok" if self.success else "fail"
        return f"<MetricSample job={self.job_name!r} dur={self.duration_seconds:.2f}s {status}>"


@dataclass
class JobMetricsSummary:
    job_name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    avg_duration: float
    min_duration: float
    max_duration: float


class MetricsStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._samples: List[MetricSample] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            data = json.loads(self._path.read_text())
            self._samples = [MetricSample.from_dict(d) for d in data]

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps([s.to_dict() for s in self._samples], indent=2))

    def record(self, sample: MetricSample) -> MetricSample:
        self._samples.append(sample)
        self._persist()
        return sample

    def samples_for(self, job_name: str) -> List[MetricSample]:
        return [s for s in self._samples if s.job_name == job_name]

    def summarize(self, job_name: str) -> Optional[JobMetricsSummary]:
        samples = self.samples_for(job_name)
        if not samples:
            return None
        durations = [s.duration_seconds for s in samples]
        successes = sum(1 for s in samples if s.success)
        return JobMetricsSummary(
            job_name=job_name,
            total_runs=len(samples),
            successful_runs=successes,
            failed_runs=len(samples) - successes,
            avg_duration=sum(durations) / len(durations),
            min_duration=min(durations),
            max_duration=max(durations),
        )

    def all_job_names(self) -> List[str]:
        return sorted({s.job_name for s in self._samples})
