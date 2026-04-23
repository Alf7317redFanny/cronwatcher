"""Concurrency control — limit how many instances of a job can run simultaneously."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ConcurrencyPolicy:
    max_instances: int = 1
    per_job_overrides: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.max_instances < 1:
            raise ValueError("max_instances must be >= 1")
        for job, val in self.per_job_overrides.items():
            if val < 1:
                raise ValueError(f"max_instances for '{job}' must be >= 1")

    def limit_for(self, job_name: str) -> int:
        return self.per_job_overrides.get(job_name, self.max_instances)


@dataclass
class ConcurrencySlot:
    job_name: str
    pid: int
    started_at: str

    def to_dict(self) -> dict:
        return {"job_name": self.job_name, "pid": self.pid, "started_at": self.started_at}

    @classmethod
    def from_dict(cls, d: dict) -> "ConcurrencySlot":
        return cls(job_name=d["job_name"], pid=d["pid"], started_at=d["started_at"])

    def __repr__(self) -> str:
        return f"<ConcurrencySlot job={self.job_name!r} pid={self.pid} started={self.started_at}>"


class ConcurrencyLimitError(Exception):
    """Raised when a job has reached its concurrency limit."""


class ConcurrencyManager:
    def __init__(self, policy: ConcurrencyPolicy, state_file: Path) -> None:
        self._policy = policy
        self._path = Path(state_file)
        self._slots: List[ConcurrencySlot] = []
        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        if self._path.exists():
            data = json.loads(self._path.read_text())
            self._slots = [ConcurrencySlot.from_dict(s) for s in data]

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps([s.to_dict() for s in self._slots], indent=2))

    # ------------------------------------------------------------------
    def active_for(self, job_name: str) -> List[ConcurrencySlot]:
        return [s for s in self._slots if s.job_name == job_name]

    def acquire(self, job_name: str, pid: Optional[int] = None) -> ConcurrencySlot:
        limit = self._policy.limit_for(job_name)
        if len(self.active_for(job_name)) >= limit:
            raise ConcurrencyLimitError(
                f"Job '{job_name}' already has {limit} active instance(s)."
            )
        slot = ConcurrencySlot(
            job_name=job_name,
            pid=pid if pid is not None else os.getpid(),
            started_at=datetime.utcnow().isoformat(),
        )
        self._slots.append(slot)
        self._save()
        return slot

    def release(self, slot: ConcurrencySlot) -> None:
        self._slots = [s for s in self._slots if not (s.job_name == slot.job_name and s.pid == slot.pid)]
        self._save()

    def release_all(self, job_name: str) -> int:
        before = len(self._slots)
        self._slots = [s for s in self._slots if s.job_name != job_name]
        self._save()
        return before - len(self._slots)
