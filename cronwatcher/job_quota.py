"""Per-job run quota enforcement: limit how many times a job may run within a time window."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class QuotaPolicy:
    max_runs: int = 0          # 0 means unlimited
    window_seconds: int = 3600
    per_job: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.max_runs < 0:
            raise ValueError("max_runs must be >= 0")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        for job, limit in self.per_job.items():
            if limit < 0:
                raise ValueError(f"per_job limit for '{job}' must be >= 0")

    def limit_for(self, job_name: str) -> int:
        return self.per_job.get(job_name, self.max_runs)


@dataclass
class QuotaState:
    job_name: str
    timestamps: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"job_name": self.job_name, "timestamps": self.timestamps}

    @classmethod
    def from_dict(cls, data: dict) -> "QuotaState":
        return cls(job_name=data["job_name"], timestamps=data.get("timestamps", []))


class QuotaManager:
    def __init__(self, policy: QuotaPolicy, state_file: Path) -> None:
        self.policy = policy
        self.state_file = state_file
        self._states: Dict[str, QuotaState] = {}
        self._load()

    def _load(self) -> None:
        if self.state_file.exists():
            data = json.loads(self.state_file.read_text())
            for entry in data:
                s = QuotaState.from_dict(entry)
                self._states[s.job_name] = s

    def _save(self) -> None:
        self.state_file.write_text(
            json.dumps([s.to_dict() for s in self._states.values()], indent=2)
        )

    def _prune(self, state: QuotaState) -> None:
        cutoff = time.time() - self.policy.window_seconds
        state.timestamps = [t for t in state.timestamps if t >= cutoff]

    def allowed(self, job_name: str) -> bool:
        limit = self.policy.limit_for(job_name)
        if limit == 0:
            return True
        state = self._states.setdefault(job_name, QuotaState(job_name=job_name))
        self._prune(state)
        return len(state.timestamps) < limit

    def record(self, job_name: str) -> None:
        state = self._states.setdefault(job_name, QuotaState(job_name=job_name))
        self._prune(state)
        state.timestamps.append(time.time())
        self._save()

    def usage(self, job_name: str) -> int:
        state = self._states.get(job_name, QuotaState(job_name=job_name))
        self._prune(state)
        return len(state.timestamps)
