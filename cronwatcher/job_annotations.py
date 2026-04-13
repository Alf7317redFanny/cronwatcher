"""Attach arbitrary key-value annotations to jobs and query them."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, Optional

from cronwatcher.config import JobConfig


@dataclass
class AnnotationIndex:
    """Stores free-form string annotations keyed by job name."""

    _data: Dict[str, Dict[str, str]] = field(default_factory=dict, init=False)

    def set(self, job: JobConfig, key: str, value: str) -> None:
        """Set *key* to *value* for *job*, overwriting any previous value."""
        if not key:
            raise ValueError("Annotation key must not be empty")
        self._data.setdefault(job.name, {})[key] = value

    def get(self, job: JobConfig, key: str) -> Optional[str]:
        """Return the annotation value or *None* if not set."""
        return self._data.get(job.name, {}).get(key)

    def all_for_job(self, job: JobConfig) -> Dict[str, str]:
        """Return a copy of all annotations for *job*."""
        return dict(self._data.get(job.name, {}))

    def jobs_with_key(self, key: str) -> Iterator[str]:
        """Yield job names that have *key* set."""
        for job_name, annotations in self._data.items():
            if key in annotations:
                yield job_name

    def jobs_with_annotation(self, key: str, value: str) -> Iterator[str]:
        """Yield job names where *key* equals *value*."""
        for job_name, annotations in self._data.items():
            if annotations.get(key) == value:
                yield job_name

    def remove(self, job: JobConfig, key: str) -> bool:
        """Remove *key* from *job*. Returns True if it existed."""
        bucket = self._data.get(job.name, {})
        if key in bucket:
            del bucket[key]
            return True
        return False

    def clear(self, job: JobConfig) -> None:
        """Remove all annotations for *job*."""
        self._data.pop(job.name, None)
