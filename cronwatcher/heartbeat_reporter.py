"""Produces human-readable and dict-based heartbeat status reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from cronwatcher.job_heartbeat import HeartbeatIndex, HeartbeatRecord


@dataclass
class HeartbeatReport:
    total: int
    stale: int
    healthy: int
    entries: List[dict]

    def as_text(self) -> str:
        lines = [f"Heartbeat Report — {self.total} jobs tracked"]
        lines.append(f"  Healthy : {self.healthy}")
        lines.append(f"  Stale   : {self.stale}")
        if self.entries:
            lines.append("")
            lines.append("  Job                          Last Seen                 Status")
            lines.append("  " + "-" * 60)
            for e in self.entries:
                status = "STALE" if e["stale"] else "ok"
                lines.append(f"  {e['job_name']:<28} {e['last_seen']:<25} {status}")
        return "\n".join(lines)

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "stale": self.stale,
            "healthy": self.healthy,
            "entries": self.entries,
        }


class HeartbeatReporter:
    def __init__(self, index: HeartbeatIndex, now: Optional[datetime] = None) -> None:
        self._index = index
        self._now = now or datetime.utcnow()

    def build(self) -> HeartbeatReport:
        records = self._index.all()
        entries = []
        for rec in sorted(records, key=lambda r: r.job_name):
            entries.append({
                "job_name": rec.job_name,
                "last_seen": rec.last_seen.isoformat(),
                "interval_seconds": rec.interval_seconds,
                "stale": rec.is_stale(self._now),
            })
        stale_count = sum(1 for e in entries if e["stale"])
        return HeartbeatReport(
            total=len(entries),
            stale=stale_count,
            healthy=len(entries) - stale_count,
            entries=entries,
        )
