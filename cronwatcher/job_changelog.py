"""Tracks configuration changes for cron jobs over time."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ChangelogEntry:
    job_name: str
    field: str
    old_value: Optional[str]
    new_value: Optional[str]
    changed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "changed_at": self.changed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChangelogEntry":
        return cls(
            job_name=data["job_name"],
            field=data["field"],
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            changed_at=datetime.fromisoformat(data["changed_at"]),
        )

    def __repr__(self) -> str:
        return (
            f"ChangelogEntry(job={self.job_name!r}, field={self.field!r}, "
            f"{self.old_value!r} -> {self.new_value!r})"
        )


class ChangelogIndex:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._entries: List[ChangelogEntry] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        raw = json.loads(self._path.read_text())
        self._entries = [ChangelogEntry.from_dict(r) for r in raw]

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps([e.to_dict() for e in self._entries], indent=2))

    def record(self, job_name: str, field: str, old_value: Optional[str], new_value: Optional[str]) -> ChangelogEntry:
        entry = ChangelogEntry(job_name=job_name, field=field, old_value=old_value, new_value=new_value)
        self._entries.append(entry)
        self._save()
        return entry

    def for_job(self, job_name: str) -> List[ChangelogEntry]:
        return [e for e in self._entries if e.job_name == job_name]

    def all(self) -> List[ChangelogEntry]:
        return list(self._entries)

    def fields_changed(self, job_name: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for e in self.for_job(job_name):
            counts[e.field] = counts.get(e.field, 0) + 1
        return counts
