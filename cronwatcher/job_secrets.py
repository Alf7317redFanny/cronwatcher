"""Manage secret references for cron job environment variables.

Secrets are stored as named references (e.g. env var names pointing to
secret keys) rather than plaintext values.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SecretRef:
    """A reference to a secret value by key."""
    key: str
    description: str = ""

    def __post_init__(self) -> None:
        if not self.key or not self.key.strip():
            raise ValueError("SecretRef key must not be empty")
        self.key = self.key.strip()

    def __repr__(self) -> str:
        return f"SecretRef(key={self.key!r})"


class SecretIndex:
    """Maps job names to their secret references."""

    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, SecretRef]] = {}

    def set(self, job_name: str, env_var: str, ref: SecretRef) -> None:
        """Associate a secret reference with an env var for a job."""
        if job_name not in self._data:
            self._data[job_name] = {}
        self._data[job_name][env_var] = ref

    def get(self, job_name: str, env_var: str) -> Optional[SecretRef]:
        """Return the secret ref for the given job and env var, or None."""
        return self._data.get(job_name, {}).get(env_var)

    def all_for_job(self, job_name: str) -> Dict[str, SecretRef]:
        """Return all secret refs for a job, keyed by env var name."""
        return dict(self._data.get(job_name, {}))

    def remove(self, job_name: str, env_var: str) -> bool:
        """Remove a secret ref. Returns True if it existed."""
        job_secrets = self._data.get(job_name, {})
        if env_var in job_secrets:
            del job_secrets[env_var]
            return True
        return False

    def jobs_with_secret(self, key: str) -> List[str]:
        """Return all job names that reference the given secret key."""
        return [
            job
            for job, refs in self._data.items()
            if any(r.key == key for r in refs.values())
        ]

    def env_vars_for_job(self, job_name: str) -> List[str]:
        """Return all env var names that have secret refs for a job."""
        return list(self._data.get(job_name, {}).keys())
