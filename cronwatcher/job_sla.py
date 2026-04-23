"""SLA (Service Level Agreement) tracking for cron jobs."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class SLAPolicy:
    """Defines the SLA requirements for a job."""
    max_duration_seconds: float = 3600.0
    min_success_rate: float = 0.95
    per_job: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.max_duration_seconds <= 0:
            raise ValueError("max_duration_seconds must be positive")
        if not (0.0 <= self.min_success_rate <= 1.0):
            raise ValueError("min_success_rate must be between 0.0 and 1.0")

    def max_duration_for(self, job_name: str) -> float:
        return self.per_job.get(job_name, self.max_duration_seconds)


@dataclass
class SLAViolation:
    job_name: str
    violation_type: str  # "duration" or "success_rate"
    detail: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "violation_type": self.violation_type,
            "detail": self.detail,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SLAViolation":
        return cls(
            job_name=data["job_name"],
            violation_type=data["violation_type"],
            detail=data["detail"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )

    def __repr__(self) -> str:
        return f"<SLAViolation job={self.job_name!r} type={self.violation_type!r}>"


class SLATracker:
    """Records and retrieves SLA violations."""

    def __init__(self, state_file: Path, policy: SLAPolicy) -> None:
        self._path = state_file
        self.policy = policy
        self._violations: List[SLAViolation] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            raw = json.loads(self._path.read_text())
            self._violations = [SLAViolation.from_dict(v) for v in raw]

    def _save(self) -> None:
        self._path.write_text(json.dumps([v.to_dict() for v in self._violations], indent=2))

    def check_duration(self, job_name: str, duration_seconds: float) -> Optional[SLAViolation]:
        limit = self.policy.max_duration_for(job_name)
        if duration_seconds > limit:
            v = SLAViolation(
                job_name=job_name,
                violation_type="duration",
                detail=f"ran for {duration_seconds:.1f}s, limit is {limit:.1f}s",
            )
            self._violations.append(v)
            self._save()
            return v
        return None

    def check_success_rate(self, job_name: str, rate: float) -> Optional[SLAViolation]:
        if rate < self.policy.min_success_rate:
            v = SLAViolation(
                job_name=job_name,
                violation_type="success_rate",
                detail=f"success rate {rate:.2%}, minimum is {self.policy.min_success_rate:.2%}",
            )
            self._violations.append(v)
            self._save()
            return v
        return None

    def violations_for(self, job_name: str) -> List[SLAViolation]:
        return [v for v in self._violations if v.job_name == job_name]

    def all_violations(self) -> List[SLAViolation]:
        return list(self._violations)

    def clear(self, job_name: Optional[str] = None) -> None:
        if job_name:
            self._violations = [v for v in self._violations if v.job_name != job_name]
        else:
            self._violations = []
        self._save()
