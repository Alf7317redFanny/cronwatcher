"""Arbitrary key-value label support for cron jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatcher.config import JobConfig


@dataclass
class LabelIndex:
    """Maps jobs to labels and supports label-based lookup."""

    _labels: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def set(self, job: JobConfig, key: str, value: str) -> None:
        """Attach a label key=value to a job."""
        if not key:
            raise ValueError("Label key must not be empty")
        self._labels.setdefault(job.name, {})[key] = value

    def get(self, job: JobConfig, key: str) -> Optional[str]:
        """Return the label value for a job, or None if absent."""
        return self._labels.get(job.name, {}).get(key)

    def labels_for_job(self, job: JobConfig) -> Dict[str, str]:
        """Return all labels attached to a job."""
        return dict(self._labels.get(job.name, {}))

    def jobs_with_label(self, key: str, value: Optional[str] = None) -> List[str]:
        """Return job names that have the given label key (and optionally value)."""
        result = []
        for job_name, labels in self._labels.items():
            if key in labels:
                if value is None or labels[key] == value:
                    result.append(job_name)
        return sorted(result)

    def remove(self, job: JobConfig, key: str) -> None:
        """Remove a label from a job. No-op if not present."""
        self._labels.get(job.name, {}).pop(key, None)

    def all_label_keys(self) -> List[str]:
        """Return a sorted list of all distinct label keys across all jobs."""
        keys: set = set()
        for labels in self._labels.values():
            keys.update(labels.keys())
        return sorted(keys)


def build(jobs: List[JobConfig], label_data: Dict[str, Dict[str, str]]) -> LabelIndex:
    """Build a LabelIndex from a mapping of {job_name: {key: value}}."""
    index = LabelIndex()
    job_map = {j.name: j for j in jobs}
    for job_name, labels in label_data.items():
        if job_name not in job_map:
            continue
        for key, value in labels.items():
            index.set(job_map[job_name], key, value)
    return index
