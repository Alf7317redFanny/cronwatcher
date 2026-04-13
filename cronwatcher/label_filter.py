"""Filter jobs by key-value labels."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatcher.config import JobConfig
from cronwatcher.job_labels import LabelIndex


@dataclass
class LabelFilterCriteria:
    """Labels that a job must carry to pass the filter."""

    # Each entry is key -> required value (None means key must exist, any value)
    required: Dict[str, Optional[str]] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not self.required


class LabelFilter:
    def __init__(self, index: LabelIndex) -> None:
        self._index = index

    def apply(
        self,
        jobs: List[JobConfig],
        criteria: LabelFilterCriteria,
    ) -> List[JobConfig]:
        """Return jobs that satisfy all label requirements."""
        if criteria.is_empty():
            return list(jobs)

        result = []
        for job in jobs:
            labels = self._index.labels_for_job(job)
            if self._matches(labels, criteria):
                result.append(job)
        return result

    @staticmethod
    def _matches(
        labels: Dict[str, str],
        criteria: LabelFilterCriteria,
    ) -> bool:
        for key, expected in criteria.required.items():
            if key not in labels:
                return False
            if expected is not None and labels[key] != expected:
                return False
        return True
