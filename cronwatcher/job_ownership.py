"""Track ownership (team/owner) for cron jobs."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from cronwatcher.config import JobConfig


@dataclass
class OwnerRecord:
    job_name: str
    owner: str
    team: Optional[str] = None

    def to_dict(self) -> dict:
        return {"job_name": self.job_name, "owner": self.owner, "team": self.team}

    @classmethod
    def from_dict(cls, data: dict) -> "OwnerRecord":
        return cls(
            job_name=data["job_name"],
            owner=data["owner"],
            team=data.get("team"),
        )

    def __repr__(self) -> str:
        team_part = f", team={self.team!r}" if self.team else ""
        return f"OwnerRecord(job={self.job_name!r}, owner={self.owner!r}{team_part})"


class OwnershipIndex:
    def __init__(self, state_file: Optional[Path] = None) -> None:
        self._state_file = state_file
        self._records: Dict[str, OwnerRecord] = {}
        if state_file and state_file.exists():
            self._load()

    def _load(self) -> None:
        raw = json.loads(self._state_file.read_text())
        for entry in raw:
            rec = OwnerRecord.from_dict(entry)
            self._records[rec.job_name] = rec

    def _save(self) -> None:
        if self._state_file:
            data = [r.to_dict() for r in self._records.values()]
            self._state_file.write_text(json.dumps(data, indent=2))

    def set(self, job_name: str, owner: str, team: Optional[str] = None) -> OwnerRecord:
        if not owner.strip():
            raise ValueError("owner must not be blank")
        rec = OwnerRecord(job_name=job_name, owner=owner.strip(), team=team)
        self._records[job_name] = rec
        self._save()
        return rec

    def get(self, job_name: str) -> Optional[OwnerRecord]:
        return self._records.get(job_name)

    def remove(self, job_name: str) -> None:
        self._records.pop(job_name, None)
        self._save()

    def jobs_for_owner(self, owner: str) -> List[str]:
        return [name for name, rec in self._records.items() if rec.owner == owner]

    def jobs_for_team(self, team: str) -> List[str]:
        return [name for name, rec in self._records.items() if rec.team == team]

    def all_records(self) -> List[OwnerRecord]:
        return list(self._records.values())
