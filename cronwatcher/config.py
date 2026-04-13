"""Configuration loading for cronwatcher."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class JobConfig:
    name: str
    schedule: str
    command: str
    timeout: int = 60
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Job name must not be empty.")
        if not self.schedule.strip():
            raise ValueError("Job schedule must not be empty.")
        if not self.command.strip():
            raise ValueError("Job command must not be empty.")
        if self.timeout <= 0:
            raise ValueError("Job timeout must be a positive integer.")


@dataclass
class WatcherConfig:
    jobs: list[JobConfig]
    history_path: str = "cronwatcher_history.json"
    notifier: dict[str, Any] | None = None
    alert_on_missed: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WatcherConfig":
        jobs = [JobConfig(**j) for j in data.get("jobs", [])]
        return cls(
            jobs=jobs,
            history_path=data.get("history_path", "cronwatcher_history.json"),
            notifier=data.get("notifier"),
            alert_on_missed=data.get("alert_on_missed", True),
        )


def load(path: Path) -> WatcherConfig:
    """Load a WatcherConfig from a JSON file."""
    with open(path, "r") as f:
        data = json.load(f)
    return WatcherConfig.from_dict(data)
