"""Rate limiting for outbound alerts to prevent notification storms."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class RateLimitConfig:
    max_alerts: int = 5
    window_seconds: int = 3600
    state_file: str = "/tmp/cronwatcher_ratelimit.json"

    def __post_init__(self) -> None:
        if self.max_alerts < 1:
            raise ValueError("max_alerts must be >= 1")
        if self.window_seconds < 1:
            raise ValueError("window_seconds must be >= 1")


@dataclass
class RateLimitState:
    timestamps: Dict[str, list] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"timestamps": self.timestamps}

    @classmethod
    def from_dict(cls, data: dict) -> "RateLimitState":
        return cls(timestamps=data.get("timestamps", {}))


class RateLimiter:
    def __init__(self, config: RateLimitConfig) -> None:
        self.config = config
        self._state_path = Path(config.state_file)
        self._state = self._load()

    def _load(self) -> RateLimitState:
        if self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text())
                return RateLimitState.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass
        return RateLimitState()

    def _save(self) -> None:
        self._state_path.write_text(json.dumps(self._state.to_dict()))

    def _prune(self, job_name: str, now: float) -> None:
        cutoff = now - self.config.window_seconds
        self._state.timestamps[job_name] = [
            t for t in self._state.timestamps.get(job_name, []) if t > cutoff
        ]

    def is_allowed(self, job_name: str) -> bool:
        now = time.time()
        self._prune(job_name, now)
        count = len(self._state.timestamps.get(job_name, []))
        return count < self.config.max_alerts

    def record(self, job_name: str) -> None:
        now = time.time()
        self._prune(job_name, now)
        self._state.timestamps.setdefault(job_name, []).append(now)
        self._save()

    def remaining(self, job_name: str) -> int:
        now = time.time()
        self._prune(job_name, now)
        used = len(self._state.timestamps.get(job_name, []))
        return max(0, self.config.max_alerts - used)
