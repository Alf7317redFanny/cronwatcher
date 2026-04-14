"""Per-job environment variable management."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EnvVar:
    key: str
    value: str

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("EnvVar key must not be empty")
        if "=" in self.key:
            raise ValueError(f"EnvVar key must not contain '=': {self.key!r}")

    def __repr__(self) -> str:
        return f"EnvVar({self.key}={self.value!r})"


@dataclass
class EnvIndex:
    _data: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def set(self, job_name: str, key: str, value: str) -> None:
        """Set an environment variable for a job."""
        EnvVar(key=key, value=value)  # validate
        self._data.setdefault(job_name, {})[key] = value

    def get(self, job_name: str, key: str) -> Optional[str]:
        """Return the value for a key, or None if not set."""
        return self._data.get(job_name, {}).get(key)

    def all_for_job(self, job_name: str) -> Dict[str, str]:
        """Return a copy of all env vars for a job."""
        return dict(self._data.get(job_name, {}))

    def delete(self, job_name: str, key: str) -> bool:
        """Remove a key for a job. Returns True if it existed."""
        job_env = self._data.get(job_name, {})
        if key in job_env:
            del job_env[key]
            return True
        return False

    def jobs_with_key(self, key: str) -> List[str]:
        """Return all job names that have the given env key set."""
        return [name for name, env in self._data.items() if key in env]

    def merge_into(self, job_name: str, base: Dict[str, str]) -> Dict[str, str]:
        """Return base env dict updated with job-specific overrides."""
        result = dict(base)
        result.update(self._data.get(job_name, {}))
        return result
