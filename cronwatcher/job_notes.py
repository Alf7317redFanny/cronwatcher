"""Persistent freeform notes attached to jobs."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class NoteEntry:
    job_name: str
    text: str
    timestamp: str

    def __repr__(self) -> str:
        return f"NoteEntry({self.job_name!r}, {self.text[:30]!r})"

    def to_dict(self) -> dict:
        return {"job_name": self.job_name, "text": self.text, "timestamp": self.timestamp}

    @staticmethod
    def from_dict(d: dict) -> "NoteEntry":
        return NoteEntry(job_name=d["job_name"], text=d["text"], timestamp=d["timestamp"])


class NoteIndex:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._notes: Dict[str, List[NoteEntry]] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        raw = json.loads(self._path.read_text())
        for job_name, entries in raw.items():
            self._notes[job_name] = [NoteEntry.from_dict(e) for e in entries]

    def _save(self) -> None:
        data = {k: [e.to_dict() for e in v] for k, v in self._notes.items()}
        self._path.write_text(json.dumps(data, indent=2))

    def add(self, job_name: str, text: str, timestamp: str) -> NoteEntry:
        entry = NoteEntry(job_name=job_name, text=text, timestamp=timestamp)
        self._notes.setdefault(job_name, []).append(entry)
        self._save()
        return entry

    def get(self, job_name: str) -> List[NoteEntry]:
        return list(self._notes.get(job_name, []))

    def delete_all(self, job_name: str) -> int:
        removed = len(self._notes.pop(job_name, []))
        self._save()
        return removed

    def all_jobs_with_notes(self) -> List[str]:
        return sorted(k for k, v in self._notes.items() if v)
