"""Filter jobs by tag, name, or status for targeted monitoring and reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronwatcher.config import JobConfig
from cronwatcher.scheduler import JobStatus, Scheduler


@dataclass
class FilterCriteria:
    tags: List[str] = field(default_factory=list)
    name_contains: Optional[str] = None
    status: Optional[str] = None  # "ok", "failed", "unknown"

    def is_empty(self) -> bool:
        return not self.tags and self.name_contains is None and self.status is None


class JobFilter:
    def __init__(self, jobs: List[JobConfig], scheduler: Scheduler) -> None:
        self._jobs = jobs
        self._scheduler = scheduler

    def apply(self, criteria: FilterCriteria) -> List[JobConfig]:
        """Return jobs matching all supplied criteria (AND logic)."""
        if criteria.is_empty():
            return list(self._jobs)

        results = list(self._jobs)

        if criteria.tags:
            tag_set = set(criteria.tags)
            results = [
                j for j in results
                if tag_set.intersection(getattr(j, "tags", []))
            ]

        if criteria.name_contains is not None:
            needle = criteria.name_contains.lower()
            results = [j for j in results if needle in j.name.lower()]

        if criteria.status is not None:
            results = [
                j for j in results
                if self._status_matches(j, criteria.status)
            ]

        return results

    def _status_matches(self, job: JobConfig, wanted: str) -> bool:
        js: JobStatus = self._scheduler.statuses.get(job.name)
        if js is None:
            return wanted == "unknown"
        if wanted == "failed":
            return js.last_failed is not None and (
                js.last_success is None or js.last_failed > js.last_success
            )
        if wanted == "ok":
            return js.last_success is not None and (
                js.last_failed is None or js.last_success >= js.last_failed
            )
        return wanted == "unknown"
