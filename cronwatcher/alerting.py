"""Alert rate limiting and deduplication for cronwatcher."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class AlertRecord:
    job_name: str
    last_sent: float
    count: int = 1

    def __repr__(self) -> str:
        return f"AlertRecord(job={self.job_name!r}, count={self.count}, last_sent={self.last_sent:.0f})"


class AlertThrottle:
    """Prevents repeated alerts for the same job within a cooldown window."""

    def __init__(self, cooldown_seconds: int = 3600, state_path: Optional[Path] = None):
        self.cooldown_seconds = cooldown_seconds
        self.state_path = state_path
        self._records: Dict[str, AlertRecord] = {}
        if state_path:
            self._load()

    def should_alert(self, job_name: str) -> bool:
        """Return True if an alert should be sent for this job right now."""
        now = time.time()
        record = self._records.get(job_name)
        if record is None:
            return True
        return (now - record.last_sent) >= self.cooldown_seconds

    def record_alert(self, job_name: str) -> None:
        """Mark that an alert was sent for this job."""
        now = time.time()
        if job_name in self._records:
            self._records[job_name].last_sent = now
            self._records[job_name].count += 1
        else:
            self._records[job_name] = AlertRecord(job_name=job_name, last_sent=now)
        if self.state_path:
            self._save()

    def reset(self, job_name: str) -> None:
        """Clear throttle state for a job (e.g. after a successful run)."""
        self._records.pop(job_name, None)
        if self.state_path:
            self._save()

    def _load(self) -> None:
        if not self.state_path or not self.state_path.exists():
            return
        data = json.loads(self.state_path.read_text())
        for job_name, rec in data.items():
            self._records[job_name] = AlertRecord(
                job_name=job_name,
                last_sent=rec["last_sent"],
                count=rec["count"],
            )

    def _save(self) -> None:
        if not self.state_path:
            return
        data = {
            name: {"last_sent": rec.last_sent, "count": rec.count}
            for name, rec in self._records.items()
        }
        self.state_path.write_text(json.dumps(data, indent=2))
