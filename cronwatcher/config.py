"""Configuration loading and validation for cronwatcher."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class JobConfig:
    name: str
    schedule: str
    command: str
    timeout: int = 60
    tags: List[str] = field(default_factory=list)
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Job name must not be empty")
        if not self.schedule.strip():
            raise ValueError("Job schedule must not be empty")
        if not self.command.strip():
            raise ValueError("Job command must not be empty")
        if self.timeout <= 0:
            raise ValueError("timeout must be a positive integer")
        if not isinstance(self.tags, list):
            raise TypeError("tags must be a list")


@dataclass
class WatcherConfig:
    jobs: List[JobConfig]
    smtp_host: str = "localhost"
    smtp_port: int = 25
    alert_email: Optional[str] = None
    from_email: str = "cronwatcher@localhost"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WatcherConfig":
        jobs = [
            JobConfig(
                name=j["name"],
                schedule=j["schedule"],
                command=j["command"],
                timeout=j.get("timeout", 60),
                tags=j.get("tags", []),
                enabled=j.get("enabled", True),
            )
            for j in data.get("jobs", [])
        ]
        return cls(
            jobs=jobs,
            smtp_host=data.get("smtp_host", "localhost"),
            smtp_port=data.get("smtp_port", 25),
            alert_email=data.get("alert_email"),
            from_email=data.get("from_email", "cronwatcher@localhost"),
        )

    @classmethod
    def load(cls, path: str) -> "WatcherConfig":
        with open(path, "r") as fh:
            data = json.load(fh)
        return cls.from_dict(data)
