"""Runbook links and notes attached to jobs for on-call guidance."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class RunbookEntry:
    job_name: str
    url: Optional[str] = None
    steps: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"job_name": self.job_name, "url": self.url, "steps": self.steps}

    @classmethod
    def from_dict(cls, data: dict) -> "RunbookEntry":
        return cls(
            job_name=data["job_name"],
            url=data.get("url"),
            steps=data.get("steps", []),
        )

    def __repr__(self) -> str:
        url_part = f" url={self.url!r}" if self.url else ""
        return f"RunbookEntry(job={self.job_name!r}{url_part} steps={len(self.steps)})"


class RunbookIndex:
    def __init__(self, state_file: Path) -> None:
        self._path = state_file
        self._data: Dict[str, RunbookEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        raw = json.loads(self._path.read_text())
        self._data = {k: RunbookEntry.from_dict(v) for k, v in raw.items()}

    def _save(self) -> None:
        self._path.write_text(json.dumps({k: v.to_dict() for k, v in self._data.items()}, indent=2))

    def set(self, job_name: str, url: Optional[str] = None, steps: Optional[List[str]] = None) -> RunbookEntry:
        entry = RunbookEntry(job_name=job_name, url=url, steps=steps or [])
        self._data[job_name] = entry
        self._save()
        return entry

    def get(self, job_name: str) -> Optional[RunbookEntry]:
        return self._data.get(job_name)

    def remove(self, job_name: str) -> bool:
        if job_name not in self._data:
            return False
        del self._data[job_name]
        self._save()
        return True

    def all(self) -> List[RunbookEntry]:
        return list(self._data.values())
