"""Configuration loader for cronwatcher."""

import os
import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class JobConfig:
    name: str
    schedule: str
    timeout: int = 300  # seconds
    alert_email: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.name:
            raise ValueError("Job name cannot be empty")
        if not self.schedule:
            raise ValueError("Job schedule cannot be empty")
        if self.timeout <= 0:
            raise ValueError("Timeout must be a positive integer")


@dataclass
class WatcherConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    log_file: str = "/var/log/cronwatcher.log"
    state_file: str = "/tmp/cronwatcher_state.json"
    default_alert_email: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "WatcherConfig":
        jobs = [
            JobConfig(
                name=j["name"],
                schedule=j["schedule"],
                timeout=j.get("timeout", 300),
                alert_email=j.get("alert_email"),
                tags=j.get("tags", []),
            )
            for j in data.get("jobs", [])
        ]
        return cls(
            jobs=jobs,
            log_file=data.get("log_file", "/var/log/cronwatcher.log"),
            state_file=data.get("state_file", "/tmp/cronwatcher_state.json"),
            default_alert_email=data.get("default_alert_email"),
        )

    @classmethod
    def load(cls, path: str) -> "WatcherConfig":
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)
