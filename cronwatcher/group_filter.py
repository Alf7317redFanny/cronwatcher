"""Filter jobs by group membership using the GroupRegistry."""
from dataclasses import dataclass
from typing import List, Optional
from cronwatcher.config import JobConfig
from cronwatcher.job_groups import GroupRegistry


@dataclass
class GroupFilterCriteria:
    group: Optional[str] = None
    exclude_group: Optional[str] = None

    def is_empty(self) -> bool:
        return self.group is None and self.exclude_group is None


class GroupFilter:
    """Applies group-based filtering to a list of jobs."""

    def __init__(self, registry: GroupRegistry) -> None:
        self._registry = registry

    def apply(
        self,
        jobs: List[JobConfig],
        criteria: GroupFilterCriteria,
    ) -> List[JobConfig]:
        if criteria.is_empty():
            return list(jobs)

        result = list(jobs)

        if criteria.group is not None:
            group = self._registry.get(criteria.group)
            allowed = set(j.name for j in group.jobs) if group else set()
            result = [j for j in result if j.name in allowed]

        if criteria.exclude_group is not None:
            group = self._registry.get(criteria.exclude_group)
            excluded = set(j.name for j in group.jobs) if group else set()
            result = [j for j in result if j.name not in excluded]

        return result


def add_group_filter_args(parser) -> None:
    """Attach group filter arguments to an argparse parser."""
    parser.add_argument("--group", default=None, help="Only jobs in this group")
    parser.add_argument(
        "--exclude-group", default=None, dest="exclude_group",
        help="Exclude jobs in this group"
    )


def group_criteria_from_args(args) -> GroupFilterCriteria:
    return GroupFilterCriteria(
        group=getattr(args, "group", None),
        exclude_group=getattr(args, "exclude_group", None),
    )
