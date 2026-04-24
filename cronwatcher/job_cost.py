"""Track estimated compute cost per job run."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class CostRate:
    """Cost rate configuration (cost per second of runtime)."""
    default_rate: float = 0.0
    per_job: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.default_rate < 0:
            raise ValueError("default_rate must be >= 0")
        for job, rate in self.per_job.items():
            if rate < 0:
                raise ValueError(f"rate for job '{job}' must be >= 0")

    def rate_for(self, job_name: str) -> float:
        return self.per_job.get(job_name, self.default_rate)


@dataclass
class CostSample:
    job_name: str
    duration_seconds: float
    cost: float
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "duration_seconds": self.duration_seconds,
            "cost": self.cost,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CostSample":
        return cls(
            job_name=data["job_name"],
            duration_seconds=data["duration_seconds"],
            cost=data["cost"],
            timestamp=data["timestamp"],
        )

    def __repr__(self) -> str:
        return f"<CostSample job={self.job_name} cost={self.cost:.4f} duration={self.duration_seconds:.2f}s>"


class CostTracker:
    def __init__(self, rate: CostRate, state_file: Optional[Path] = None) -> None:
        self._rate = rate
        self._state_file = state_file
        self._samples: List[CostSample] = []
        if state_file:
            self._load()

    def _load(self) -> None:
        if self._state_file and self._state_file.exists():
            data = json.loads(self._state_file.read_text())
            self._samples = [CostSample.from_dict(d) for d in data]

    def _save(self) -> None:
        if self._state_file:
            self._state_file.write_text(json.dumps([s.to_dict() for s in self._samples], indent=2))

    def record(self, job_name: str, duration_seconds: float, timestamp: str) -> CostSample:
        rate = self._rate.rate_for(job_name)
        cost = rate * duration_seconds
        sample = CostSample(job_name=job_name, duration_seconds=duration_seconds, cost=cost, timestamp=timestamp)
        self._samples.append(sample)
        self._save()
        return sample

    def total_cost(self, job_name: Optional[str] = None) -> float:
        samples = self._samples if job_name is None else [s for s in self._samples if s.job_name == job_name]
        return sum(s.cost for s in samples)

    def samples_for(self, job_name: str) -> List[CostSample]:
        return [s for s in self._samples if s.job_name == job_name]

    def all_samples(self) -> List[CostSample]:
        return list(self._samples)
