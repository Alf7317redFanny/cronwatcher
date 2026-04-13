"""Persistent job run history tracking using a simple JSON file store."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class RunRecord:
    job_name: str
    ran_at: str  # ISO format
    success: bool
    exit_code: Optional[int] = None
    error_message: Optional[str] = None

    def __repr__(self) -> str:
        status = "OK" if self.success else "FAIL"
        return f"<RunRecord job={self.job_name} at={self.ran_at} status={status}>"


@dataclass
class History:
    path: str
    records: List[RunRecord] = field(default_factory=list)

    def load(self) -> None:
        """Load records from disk if the history file exists."""
        if not os.path.exists(self.path):
            return
        with open(self.path, "r") as f:
            raw = json.load(f)
        self.records = [
            RunRecord(
                job_name=r["job_name"],
                ran_at=r["ran_at"],
                success=r["success"],
                exit_code=r.get("exit_code"),
                error_message=r.get("error_message"),
            )
            for r in raw
        ]

    def save(self) -> None:
        """Persist current records to disk."""
        with open(self.path, "w") as f:
            json.dump([asdict(r) for r in self.records], f, indent=2)

    def add(self, record: RunRecord) -> None:
        """Append a new record and persist immediately."""
        self.records.append(record)
        self.save()

    def for_job(self, job_name: str) -> List[RunRecord]:
        """Return all records for a specific job, newest first."""
        return sorted(
            [r for r in self.records if r.job_name == job_name],
            key=lambda r: r.ran_at,
            reverse=True,
        )

    def last_run(self, job_name: str) -> Optional[RunRecord]:
        """Return the most recent record for a job, or None."""
        records = self.for_job(job_name)
        return records[0] if records else None


def make_record(
    job_name: str,
    success: bool,
    exit_code: Optional[int] = None,
    error_message: Optional[str] = None,
) -> RunRecord:
    return RunRecord(
        job_name=job_name,
        ran_at=datetime.utcnow().isoformat(),
        success=success,
        exit_code=exit_code,
        error_message=error_message,
    )
