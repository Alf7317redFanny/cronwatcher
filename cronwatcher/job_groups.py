"""Group jobs by arbitrary labels for bulk operations and reporting."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from cronwatcher.config import JobConfig


@dataclass
class JobGroup:
    name: str
    jobs: List[JobConfig] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"<JobGroup name={self.name!r} jobs={len(self.jobs)}>"

    def add(self, job: JobConfig) -> None:
        if job not in self.jobs:
            self.jobs.append(job)

    def remove(self, job_name: str) -> None:
        self.jobs = [j for j in self.jobs if j.name != job_name]


class GroupRegistry:
    """Maintains a registry of named job groups."""

    def __init__(self) -> None:
        self._groups: Dict[str, JobGroup] = {}

    def create(self, name: str) -> JobGroup:
        if name in self._groups:
            raise ValueError(f"Group {name!r} already exists")
        group = JobGroup(name=name)
        self._groups[name] = group
        return group

    def get(self, name: str) -> Optional[JobGroup]:
        return self._groups.get(name)

    def get_or_create(self, name: str) -> JobGroup:
        if name not in self._groups:
            self._groups[name] = JobGroup(name=name)
        return self._groups[name]

    def assign(self, group_name: str, job: JobConfig) -> None:
        self.get_or_create(group_name).add(job)

    def unassign(self, group_name: str, job_name: str) -> None:
        group = self._groups.get(group_name)
        if group:
            group.remove(job_name)

    def groups_for_job(self, job_name: str) -> List[str]:
        return [
            name
            for name, group in self._groups.items()
            if any(j.name == job_name for j in group.jobs)
        ]

    def all_group_names(self) -> List[str]:
        return sorted(self._groups.keys())

    def build_from_tags(self, jobs: List[JobConfig]) -> None:
        """Auto-assign jobs to groups based on their tags field if present."""
        for job in jobs:
            tags = getattr(job, "tags", []) or []
            for tag in tags:
                self.assign(tag, job)
