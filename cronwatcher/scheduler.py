from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from croniter import croniter

from cronwatcher.config import JobConfig


@dataclass
class JobStatus:
    job_name: str
    last_run: Optional[datetime] = None
    next_expected: Optional[datetime] = None
    missed: bool = False
    failed: bool = False
    failure_reason: Optional[str] = None

    def mark_ran(self, at: Optional[datetime] = None) -> None:
        self.last_run = at or datetime.now(timezone.utc)
        self.missed = False
        self.failed = False
        self.failure_reason = None

    def mark_failed(self, reason: str, at: Optional[datetime] = None) -> None:
        self.last_run = at or datetime.now(timezone.utc)
        self.failed = True
        self.failure_reason = reason

    def __repr__(self) -> str:
        return (
            f"JobStatus(name={self.job_name!r}, last_run={self.last_run}, "
            f"missed={self.missed}, failed={self.failed})"
        )


class Scheduler:
    def __init__(self, jobs: list[JobConfig]) -> None:
        self.jobs = {job.name: job for job in jobs}
        self.statuses: dict[str, JobStatus] = {
            job.name: JobStatus(job_name=job.name) for job in jobs
        }

    def compute_next_expected(self, job_name: str, after: Optional[datetime] = None) -> Optional[datetime]:
        job = self.jobs.get(job_name)
        if job is None:
            return None
        base = after or datetime.now(timezone.utc)
        cron = croniter(job.schedule, base)
        return cron.get_next(datetime)

    def check_missed(self, now: Optional[datetime] = None) -> list[str]:
        now = now or datetime.now(timezone.utc)
        missed = []
        for name, status in self.statuses.items():
            if status.next_expected and now > status.next_expected:
                status.missed = True
                missed.append(name)
        return missed

    def record_run(self, job_name: str, success: bool = True, reason: Optional[str] = None) -> None:
        status = self.statuses.get(job_name)
        if status is None:
            raise KeyError(f"Unknown job: {job_name!r}")
        if success:
            status.mark_ran()
        else:
            status.mark_failed(reason or "unknown error")
        status.next_expected = self.compute_next_expected(job_name, after=status.last_run)

    def get_status(self, job_name: str) -> JobStatus:
        if job_name not in self.statuses:
            raise KeyError(f"Unknown job: {job_name!r}")
        return self.statuses[job_name]
