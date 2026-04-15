"""Exclusive execution locks for cron jobs to prevent overlapping runs."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class LockInfo:
    job_name: str
    pid: int
    acquired_at: float

    def __repr__(self) -> str:
        return f"LockInfo(job={self.job_name!r}, pid={self.pid}, age={time.time() - self.acquired_at:.1f}s)"

    def to_dict(self) -> dict:
        return {"job_name": self.job_name, "pid": self.pid, "acquired_at": self.acquired_at}

    @staticmethod
    def from_dict(data: dict) -> "LockInfo":
        return LockInfo(
            job_name=data["job_name"],
            pid=int(data["pid"]),
            acquired_at=float(data["acquired_at"]),
        )


class LockError(Exception):
    """Raised when a lock cannot be acquired."""


@dataclass
class JobLockManager:
    lock_dir: Path
    _locks: Dict[str, LockInfo] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.lock_dir = Path(self.lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    def _lock_path(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return self.lock_dir / f"{safe}.lock"

    def acquire(self, job_name: str) -> LockInfo:
        """Acquire a lock for job_name. Raises LockError if already locked."""
        path = self._lock_path(job_name)
        if path.exists():
            raw = path.read_text().strip().split("|")
            existing = LockInfo(job_name=raw[0], pid=int(raw[1]), acquired_at=float(raw[2]))
            raise LockError(f"Job '{job_name}' is already locked: {existing}")
        info = LockInfo(job_name=job_name, pid=os.getpid(), acquired_at=time.time())
        path.write_text(f"{info.job_name}|{info.pid}|{info.acquired_at}")
        self._locks[job_name] = info
        return info

    def release(self, job_name: str) -> None:
        """Release the lock for job_name. No-op if not held."""
        path = self._lock_path(job_name)
        if path.exists():
            path.unlink()
        self._locks.pop(job_name, None)

    def is_locked(self, job_name: str) -> bool:
        return self._lock_path(job_name).exists()

    def current_lock(self, job_name: str) -> Optional[LockInfo]:
        path = self._lock_path(job_name)
        if not path.exists():
            return None
        raw = path.read_text().strip().split("|")
        return LockInfo(job_name=raw[0], pid=int(raw[1]), acquired_at=float(raw[2]))

    def release_all(self) -> None:
        for name in list(self._locks):
            self.release(name)
