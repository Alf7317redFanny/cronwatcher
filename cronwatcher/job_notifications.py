"""Per-job notification preferences and routing."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
from pathlib import Path


VALID_CHANNELS = {"email", "webhook", "log", "slack"}


@dataclass
class NotificationPrefs:
    channels: List[str] = field(default_factory=lambda: ["log"])
    on_failure: bool = True
    on_missed: bool = True
    on_recovery: bool = False

    def __post_init__(self) -> None:
        for ch in self.channels:
            if ch not in VALID_CHANNELS:
                raise ValueError(f"Unknown notification channel: {ch!r}")

    def to_dict(self) -> dict:
        return {
            "channels": self.channels,
            "on_failure": self.on_failure,
            "on_missed": self.on_missed,
            "on_recovery": self.on_recovery,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NotificationPrefs":
        return cls(
            channels=data.get("channels", ["log"]),
            on_failure=data.get("on_failure", True),
            on_missed=data.get("on_missed", True),
            on_recovery=data.get("on_recovery", False),
        )


class NotificationIndex:
    def __init__(self, state_file: Optional[str] = None) -> None:
        self._prefs: Dict[str, NotificationPrefs] = {}
        self._path = Path(state_file) if state_file else None
        if self._path and self._path.exists():
            self._load()

    def set(self, job_name: str, prefs: NotificationPrefs) -> None:
        self._prefs[job_name] = prefs
        self._save()

    def get(self, job_name: str) -> NotificationPrefs:
        return self._prefs.get(job_name, NotificationPrefs())

    def all(self) -> Dict[str, NotificationPrefs]:
        return dict(self._prefs)

    def remove(self, job_name: str) -> bool:
        removed = self._prefs.pop(job_name, None) is not None
        if removed:
            self._save()
        return removed

    def _save(self) -> None:
        if self._path:
            self._path.write_text(
                json.dumps({k: v.to_dict() for k, v in self._prefs.items()}, indent=2)
            )

    def _load(self) -> None:
        data = json.loads(self._path.read_text())
        self._prefs = {k: NotificationPrefs.from_dict(v) for k, v in data.items()}
