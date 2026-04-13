from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from cronwatcher.scheduler import Scheduler, JobStatus
from cronwatcher.notifier import Notifier
from cronwatcher.config import JobConfig


@dataclass
class MissedRun:
    job_name: str
    expected_at: datetime
    last_ran: Optional[datetime]

    def __repr__(self) -> str:
        last = self.last_ran.isoformat() if self.last_ran else "never"
        return f"MissedRun(job={self.job_name}, expected={self.expected_at.isoformat()}, last_ran={last})"


class Monitor:
    def __init__(self, scheduler: Scheduler, notifier: Notifier) -> None:
        self.scheduler = scheduler
        self.notifier = notifier

    def check_missed_runs(self, jobs: list[JobConfig]) -> list[MissedRun]:
        """Check all jobs for missed runs based on their schedule."""
        missed: list[MissedRun] = []
        now = datetime.now(tz=timezone.utc)

        for job in jobs:
            status: JobStatus = self.scheduler.statuses.get(job.name)
            if status is None:
                continue

            next_run = status.next_run
            if next_run is None:
                continue

            if now > next_run:
                missed.append(
                    MissedRun(
                        job_name=job.name,
                        expected_at=next_run,
                        last_ran=status.last_ran,
                    )
                )

        return missed

    def alert_missed_runs(self, jobs: list[JobConfig]) -> int:
        """Send alerts for any missed runs. Returns count of alerts sent."""
        missed = self.check_missed_runs(jobs)

        for run in missed:
            last = run.last_ran.isoformat() if run.last_ran else "never"
            subject = f"[cronwatcher] Missed run: {run.job_name}"
            body = (
                f"Job '{run.job_name}' missed its scheduled run.\n"
                f"Expected at: {run.expected_at.isoformat()}\n"
                f"Last ran: {last}"
            )
            self.notifier.send_alert(subject, body)

        return len(missed)
