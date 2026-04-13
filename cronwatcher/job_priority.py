"""Job priority levels and ordering utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Sequence

from cronwatcher.config import JobConfig


class Priority(IntEnum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

    @classmethod
    def from_str(cls, value: str) -> "Priority":
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(
                f"Unknown priority '{value}'. "
                f"Valid options: {[p.name for p in cls]}"
            )


@dataclass
class PriorityIndex:
    """Maps job names to their assigned Priority."""

    _data: Dict[str, Priority] = field(default_factory=dict, init=False)

    def set(self, job_name: str, priority: Priority) -> None:
        self._data[job_name] = priority

    def get(self, job_name: str) -> Priority:
        return self._data.get(job_name, Priority.NORMAL)

    def sorted_jobs(
        self, jobs: Sequence[JobConfig], descending: bool = True
    ) -> List[JobConfig]:
        """Return jobs sorted by priority (highest first by default)."""
        return sorted(
            jobs,
            key=lambda j: self.get(j.name),
            reverse=descending,
        )

    def jobs_at(
        self, jobs: Sequence[JobConfig], priority: Priority
    ) -> List[JobConfig]:
        """Return only jobs that match the given priority level."""
        return [j for j in jobs if self.get(j.name) == priority]


def build_priority_index(
    jobs: Sequence[JobConfig],
    priority_map: Dict[str, str],
) -> PriorityIndex:
    """Build a PriorityIndex from a plain string mapping (e.g. from config)."""
    index = PriorityIndex()
    for job in jobs:
        raw = priority_map.get(job.name)
        if raw is not None:
            index.set(job.name, Priority.from_str(raw))
    return index
