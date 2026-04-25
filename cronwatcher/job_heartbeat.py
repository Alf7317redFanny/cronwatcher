"""Heartbeat tracking for cron jobs — records last seen time and detects stale jobs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class HeartbeatRecord:
    job_name: str
    last_seen: datetime
    interval_seconds: int

    def is_stale(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.utcnow()
        return (now - self.last_seen).total_seconds() > self.interval_seconds

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "last_seen": self.last_seen.isoformat(),
            "interval_seconds": self.interval_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HeartbeatRecord":
        return cls(
            job_name=data["job_name"],
            last_seen=datetime.fromisoformat(data["last_seen"]),
            interval_seconds=data["interval_seconds"],
        )

    def __repr__(self) -> str:
        stale = "stale" if self.is_stale() else "ok"
        return f"<HeartbeatRecord job={self.job_name!r} last_seen={self.last_seen.isoformat()} [{stale}]>"


class HeartbeatIndex:
    def __init__(self, state_file: Path, default_interval: int = 3600) -> None:
        self._path = state_file
        self.default_interval = default_interval
        self._records: Dict[str, HeartbeatRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        data = json.loads(self._path.read_text())
        for entry in data:
            rec = HeartbeatRecord.from_dict(entry)
            self._records[rec.job_name] = rec

    def _save(self) -> None:
        self._path.write_text(
            json.dumps([r.to_dict() for r in self._records.values()], indent=2)
        )

    def ping(self, job_name: str, interval_seconds: Optional[int] = None) -> HeartbeatRecord:
        interval = interval_seconds if interval_seconds is not None else self.default_interval
        rec = HeartbeatRecord(
            job_name=job_name,
            last_seen=datetime.utcnow(),
            interval_seconds=interval,
        )
        self._records[job_name] = rec
        self._save()
        return rec

    def get(self, job_name: str) -> Optional[HeartbeatRecord]:
        return self._records.get(job_name)

    def stale_jobs(self, now: Optional[datetime] = None) -> List[HeartbeatRecord]:
        return [r for r in self._records.values() if r.is_stale(now)]

    def all(self) -> List[HeartbeatRecord]:
        return list(self._records.values())
