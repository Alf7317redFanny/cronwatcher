"""Track checksums of job command strings to detect unexpected changes."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from cronwatcher.config import JobConfig


@dataclass
class ChecksumRecord:
    job_name: str
    checksum: str

    def to_dict(self) -> dict:
        return {"job_name": self.job_name, "checksum": self.checksum}

    @classmethod
    def from_dict(cls, data: dict) -> "ChecksumRecord":
        return cls(job_name=data["job_name"], checksum=data["checksum"])

    def __repr__(self) -> str:
        return f"ChecksumRecord(job={self.job_name!r}, checksum={self.checksum[:8]}...)"


def compute_checksum(job: JobConfig) -> str:
    """Return a SHA-256 hex digest of the job's command string."""
    return hashlib.sha256(job.command.encode()).hexdigest()


class ChecksumIndex:
    """Persist and compare job command checksums to detect drift."""

    def __init__(self, state_file: Path) -> None:
        self._path = state_file
        self._records: Dict[str, ChecksumRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        raw = json.loads(self._path.read_text())
        for item in raw:
            rec = ChecksumRecord.from_dict(item)
            self._records[rec.job_name] = rec

    def _save(self) -> None:
        self._path.write_text(
            json.dumps([r.to_dict() for r in self._records.values()], indent=2)
        )

    def record(self, job: JobConfig) -> ChecksumRecord:
        """Store (or update) the checksum for *job* and return the record."""
        rec = ChecksumRecord(job_name=job.name, checksum=compute_checksum(job))
        self._records[job.name] = rec
        self._save()
        return rec

    def get(self, job_name: str) -> Optional[ChecksumRecord]:
        """Return the stored record for *job_name*, or None if unseen."""
        return self._records.get(job_name)

    def has_changed(self, job: JobConfig) -> bool:
        """Return True if the job's command differs from the stored checksum."""
        existing = self.get(job.name)
        if existing is None:
            return False  # never recorded — not a change, just new
        return existing.checksum != compute_checksum(job)

    def all_records(self) -> list:
        return list(self._records.values())
