"""Audit log for cronwatcher — records significant system events to a file."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class AuditEvent:
    timestamp: str
    event_type: str
    job_name: Optional[str]
    detail: str

    def __repr__(self) -> str:
        return f"AuditEvent({self.event_type}, job={self.job_name}, {self.timestamp})"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEvent":
        return cls(
            timestamp=data["timestamp"],
            event_type=data["event_type"],
            job_name=data.get("job_name"),
            detail=data["detail"],
        )


class AuditLog:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._events: List[AuditEvent] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open() as fh:
            for line in fh:
                line = line.strip()
                if line:
                    self._events.append(AuditEvent.from_dict(json.loads(line)))

    def record(self, event_type: str, detail: str, job_name: Optional[str] = None) -> AuditEvent:
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            job_name=job_name,
            detail=detail,
        )
        self._events.append(event)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as fh:
            fh.write(json.dumps(event.to_dict()) + "\n")
        return event

    def events(self, event_type: Optional[str] = None, job_name: Optional[str] = None) -> List[AuditEvent]:
        result = self._events
        if event_type is not None:
            result = [e for e in result if e.event_type == event_type]
        if job_name is not None:
            result = [e for e in result if e.job_name == job_name]
        return list(result)

    def clear(self) -> None:
        self._events = []
        if self.path.exists():
            self.path.unlink()
