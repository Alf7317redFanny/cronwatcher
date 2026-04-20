"""Job cooldown — enforces a minimum gap between consecutive job runs."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional


@dataclass
class CooldownPolicy:
    default_seconds: int = 60
    per_job: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.default_seconds < 0:
            raise ValueError("default_seconds must be >= 0")
        for job, secs in self.per_job.items():
            if secs < 0:
                raise ValueError(f"cooldown for '{job}' must be >= 0")

    def seconds_for(self, job_name: str) -> int:
        return self.per_job.get(job_name, self.default_seconds)


@dataclass
class CooldownState:
    job_name: str
    last_run: datetime

    def to_dict(self) -> dict:
        return {"job_name": self.job_name, "last_run": self.last_run.isoformat()}

    @classmethod
    def from_dict(cls, data: dict) -> "CooldownState":
        return cls(
            job_name=data["job_name"],
            last_run=datetime.fromisoformat(data["last_run"]),
        )


class CooldownManager:
    def __init__(self, policy: CooldownPolicy, state_file: Path) -> None:
        self._policy = policy
        self._state_file = state_file
        self._states: Dict[str, CooldownState] = {}
        self._load()

    def _load(self) -> None:
        if not self._state_file.exists():
            return
        data = json.loads(self._state_file.read_text())
        for entry in data:
            s = CooldownState.from_dict(entry)
            self._states[s.job_name] = s

    def _save(self) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = [s.to_dict() for s in self._states.values()]
        self._state_file.write_text(json.dumps(payload, indent=2))

    def is_cooling_down(self, job_name: str, now: Optional[datetime] = None) -> bool:
        now = now or datetime.utcnow()
        state = self._states.get(job_name)
        if state is None:
            return False
        gap = timedelta(seconds=self._policy.seconds_for(job_name))
        return (now - state.last_run) < gap

    def record_run(self, job_name: str, when: Optional[datetime] = None) -> None:
        when = when or datetime.utcnow()
        self._states[job_name] = CooldownState(job_name=job_name, last_run=when)
        self._save()

    def remaining_seconds(self, job_name: str, now: Optional[datetime] = None) -> float:
        now = now or datetime.utcnow()
        state = self._states.get(job_name)
        if state is None:
            return 0.0
        gap = timedelta(seconds=self._policy.seconds_for(job_name))
        remaining = gap - (now - state.last_run)
        return max(0.0, remaining.total_seconds())
