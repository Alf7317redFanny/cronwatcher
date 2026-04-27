"""Forecast upcoming job runs based on cron schedules."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from croniter import croniter

from cronwatcher.config import JobConfig


@dataclass
class ForecastEntry:
    job_name: str
    next_runs: List[datetime] = field(default_factory=list)

    def __repr__(self) -> str:
        runs = ", ".join(dt.strftime("%Y-%m-%d %H:%M") for dt in self.next_runs)
        return f"ForecastEntry(job={self.job_name!r}, next_runs=[{runs}])"

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "next_runs": [dt.isoformat() for dt in self.next_runs],
        }


class JobForecaster:
    """Compute the next N scheduled run times for a list of jobs."""

    def __init__(self, jobs: List[JobConfig], count: int = 5) -> None:
        if count < 1:
            raise ValueError("count must be at least 1")
        self.jobs = jobs
        self.count = count

    def forecast(self, base: Optional[datetime] = None) -> List[ForecastEntry]:
        """Return a ForecastEntry per job with the next `count` run times."""
        base = base or datetime.utcnow()
        entries: List[ForecastEntry] = []
        for job in self.jobs:
            try:
                it = croniter(job.schedule, base)
                runs = [it.get_next(datetime) for _ in range(self.count)]
            except Exception:
                runs = []
            entries.append(ForecastEntry(job_name=job.name, next_runs=runs))
        return entries

    def next_run(self, job: JobConfig, base: Optional[datetime] = None) -> Optional[datetime]:
        """Return the single next run time for a job, or None on error."""
        base = base or datetime.utcnow()
        try:
            return croniter(job.schedule, base).get_next(datetime)
        except Exception:
            return None
