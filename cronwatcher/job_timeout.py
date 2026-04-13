"""Job timeout configuration and enforcement utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class TimeoutConfig:
    """Per-job timeout settings (seconds)."""
    default_seconds: int = 300
    per_job: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.default_seconds <= 0:
            raise ValueError("default_seconds must be positive")
        for job_name, secs in self.per_job.items():
            if secs <= 0:
                raise ValueError(
                    f"Timeout for job '{job_name}' must be positive, got {secs}"
                )

    def for_job(self, job_name: str) -> int:
        """Return the effective timeout for *job_name*."""
        return self.per_job.get(job_name, self.default_seconds)


@dataclass
class TimeoutViolation:
    """Record of a job that exceeded its allowed runtime."""
    job_name: str
    allowed_seconds: int
    actual_seconds: float

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"TimeoutViolation(job={self.job_name!r}, "
            f"allowed={self.allowed_seconds}s, actual={self.actual_seconds:.1f}s)"
        )


class TimeoutTracker:
    """Detects jobs whose recorded runtime exceeded their configured timeout."""

    def __init__(self, config: TimeoutConfig) -> None:
        self._config = config

    def check(self, job_name: str, elapsed_seconds: float) -> Optional[TimeoutViolation]:
        """Return a :class:`TimeoutViolation` if *elapsed_seconds* exceeds the limit."""
        limit = self._config.for_job(job_name)
        if elapsed_seconds > limit:
            return TimeoutViolation(
                job_name=job_name,
                allowed_seconds=limit,
                actual_seconds=elapsed_seconds,
            )
        return None

    def check_many(
        self, runtimes: Dict[str, float]
    ) -> list[TimeoutViolation]:
        """Check multiple jobs at once; returns violations only."""
        violations = []
        for name, elapsed in runtimes.items():
            v = self.check(name, elapsed)
            if v is not None:
                violations.append(v)
        return violations
