"""Tag-based filtering and grouping for cron jobs."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TagIndex:
    """Maps tags to job names for fast lookup."""
    _index: Dict[str, List[str]] = field(default_factory=dict)

    def build(self, jobs: List) -> None:
        """Build index from a list of JobConfig objects."""
        self._index.clear()
        for job in jobs:
            tags = getattr(job, "tags", []) or []
            for tag in tags:
                self._index.setdefault(tag, []).append(job.name)

    def jobs_for_tag(self, tag: str) -> List[str]:
        """Return job names associated with a given tag."""
        return list(self._index.get(tag, []))

    def tags_for_job(self, job_name: str) -> List[str]:
        """Return all tags associated with a given job name."""
        return [tag for tag, names in self._index.items() if job_name in names]

    def all_tags(self) -> List[str]:
        """Return sorted list of all known tags."""
        return sorted(self._index.keys())

    def filter_jobs(self, jobs: List, tags: List[str]) -> List:
        """Return only jobs that have at least one of the given tags."""
        if not tags:
            return list(jobs)
        matched_names = set()
        for tag in tags:
            matched_names.update(self.jobs_for_tag(tag))
        return [j for j in jobs if j.name in matched_names]

    def __repr__(self) -> str:
        return f"TagIndex(tags={self.all_tags()})"
