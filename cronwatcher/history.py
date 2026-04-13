"""Persistent run history for cron jobs."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class RunRecord:
    job_name: str
    ran_at: datetime
    status: str  # "success" | "failure"
    output: str
    duration: float  # seconds

    def __repr__(self) -> str:
        return f"<RunRecord job={self.job_name} status={self.status} at={self.ran_at}>"


class History:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._records: Dict[str, List[RunRecord]] = {}

    def load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open() as f:
            raw = json.load(f)
        for job_name, entries in raw.items():
            self._records[job_name] = [
                RunRecord(
                    job_name=e["job_name"],
                    ran_at=datetime.fromisoformat(e["ran_at"]),
                    status=e["status"],
                    output=e["output"],
                    duration=e["duration"],
                )
                for e in entries
            ]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            job_name: [
                {
                    "job_name": r.job_name,
                    "ran_at": r.ran_at.isoformat(),
                    "status": r.status,
                    "output": r.output,
                    "duration": r.duration,
                }
                for r in records
            ]
            for job_name, records in self._records.items()
        }
        with self.path.open("w") as f:
            json.dump(data, f, indent=2)

    def add(self, record: RunRecord) -> None:
        self._records.setdefault(record.job_name, []).append(record)
        self.save()

    def get(self, job_name: str) -> List[RunRecord]:
        return self._records.get(job_name, [])

    def get_last(self, job_name: str) -> Optional[RunRecord]:
        records = self.get(job_name)
        return records[-1] if records else None

    def all_jobs(self) -> List[str]:
        return list(self._records.keys())

    def recent(self, job_name: str, limit: int = 10) -> List[RunRecord]:
        return self.get(job_name)[-limit:]
