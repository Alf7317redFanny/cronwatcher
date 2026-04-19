from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    delay_seconds: float = 5.0
    per_job: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.delay_seconds < 0:
            raise ValueError("delay_seconds must be >= 0")
        for job, attempts in self.per_job.items():
            if attempts < 1:
                raise ValueError(f"per_job attempts for '{job}' must be >= 1")

    def attempts_for(self, job_name: str) -> int:
        return self.per_job.get(job_name, self.max_attempts)


@dataclass
class RetryState:
    job_name: str
    attempt: int = 0
    last_error: Optional[str] = None

    @property
    def exhausted(self) -> bool:
        return self._policy_attempts is not None and self.attempt >= self._policy_attempts

    def __repr__(self) -> str:
        return f"RetryState(job={self.job_name!r}, attempt={self.attempt}, last_error={self.last_error!r})"


class RetryManager:
    def __init__(self, policy: RetryPolicy) -> None:
        self._policy = policy
        self._states: Dict[str, RetryState] = {}

    def _state(self, job_name: str) -> RetryState:
        if job_name not in self._states:
            self._states[job_name] = RetryState(job_name=job_name)
        return self._states[job_name]

    def should_retry(self, job_name: str) -> bool:
        state = self._state(job_name)
        return state.attempt < self._policy.attempts_for(job_name)

    def record_attempt(self, job_name: str, error: Optional[str] = None) -> RetryState:
        state = self._state(job_name)
        state.attempt += 1
        state.last_error = error
        return state

    def reset(self, job_name: str) -> None:
        self._states.pop(job_name, None)

    def attempt_count(self, job_name: str) -> int:
        return self._state(job_name).attempt

    def delay_for(self, job_name: str) -> float:
        return self._policy.delay_seconds
