from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class PauseRecord:
    job_name: str
    reason: str = ""

    def to_dict(self) -> dict:
        return {"job_name": self.job_name, "reason": self.reason}

    @classmethod
    def from_dict(cls, d: dict) -> "PauseRecord":
        return cls(job_name=d["job_name"], reason=d.get("reason", ""))

    def __repr__(self) -> str:
        return f"PauseRecord(job={self.job_name!r}, reason={self.reason!r})"


class PauseIndex:
    def __init__(self, state_file: Path) -> None:
        self._path = state_file
        self._paused: Dict[str, PauseRecord] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            data = json.loads(self._path.read_text())
            for entry in data:
                r = PauseRecord.from_dict(entry)
                self._paused[r.job_name] = r

    def _save(self) -> None:
        self._path.write_text(json.dumps([r.to_dict() for r in self._paused.values()], indent=2))

    def pause(self, job_name: str, reason: str = "") -> PauseRecord:
        record = PauseRecord(job_name=job_name, reason=reason)
        self._paused[job_name] = record
        self._save()
        return record

    def resume(self, job_name: str) -> bool:
        if job_name in self._paused:
            del self._paused[job_name]
            self._save()
            return True
        return False

    def is_paused(self, job_name: str) -> bool:
        return job_name in self._paused

    def all_paused(self) -> List[PauseRecord]:
        return list(self._paused.values())
