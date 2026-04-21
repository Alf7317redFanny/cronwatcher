"""Point-in-time snapshots of job state for diffing and auditing."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional


@dataclass
class JobSnapshot:
    job_name: str
    timestamp: float
    last_run: Optional[float]
    last_status: Optional[str]  # "ok" | "failed" | None
    run_count: int
    failure_count: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "JobSnapshot":
        return cls(**d)

    def __repr__(self) -> str:
        ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(self.timestamp))
        return f"<JobSnapshot job={self.job_name!r} at={ts} status={self.last_status!r}>"


class SnapshotStore:
    """Persists and retrieves job snapshots from a JSON file."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._snapshots: List[JobSnapshot] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text())
            self._snapshots = [JobSnapshot.from_dict(r) for r in raw]
        except (json.JSONDecodeError, KeyError, TypeError):
            self._snapshots = []

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps([s.to_dict() for s in self._snapshots], indent=2))

    def record(self, snapshot: JobSnapshot) -> JobSnapshot:
        self._snapshots.append(snapshot)
        self._save()
        return snapshot

    def latest_for(self, job_name: str) -> Optional[JobSnapshot]:
        matches = [s for s in self._snapshots if s.job_name == job_name]
        return matches[-1] if matches else None

    def all_for(self, job_name: str) -> List[JobSnapshot]:
        return [s for s in self._snapshots if s.job_name == job_name]

    def diff(self, job_name: str) -> Optional[dict]:
        """Return a dict describing changes between the last two snapshots."""
        history = self.all_for(job_name)
        if len(history) < 2:
            return None
        prev, curr = history[-2], history[-1]
        changes: dict = {}
        for field in ("last_status", "run_count", "failure_count", "last_run"):
            pv, cv = getattr(prev, field), getattr(curr, field)
            if pv != cv:
                changes[field] = {"before": pv, "after": cv}
        return changes or None

    def all(self) -> List[JobSnapshot]:
        return list(self._snapshots)
