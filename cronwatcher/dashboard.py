"""Simple text-based dashboard for displaying cron job status in the terminal."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from cronwatcher.scheduler import JobStatus, Scheduler
from cronwatcher.history import History, RunRecord


@dataclass
class JobRow:
    name: str
    schedule: str
    last_run: Optional[datetime]
    last_status: Optional[str]
    next_run: Optional[datetime]
    run_count: int

    def status_symbol(self) -> str:
        if self.last_status is None:
            return "?"
        return "✓" if self.last_status == "success" else "✗"


class Dashboard:
    def __init__(self, scheduler: Scheduler, history: History):
        self.scheduler = scheduler
        self.history = history

    def build_rows(self) -> List[JobRow]:
        rows = []
        for name, status in self.scheduler.statuses.items():
            records = self.history.get(name)
            last_record: Optional[RunRecord] = records[-1] if records else None
            rows.append(
                JobRow(
                    name=name,
                    schedule=status.job.schedule,
                    last_run=last_record.ran_at if last_record else None,
                    last_status=last_record.status if last_record else None,
                    next_run=status.next_run,
                    run_count=len(records),
                )
            )
        return rows

    def render(self) -> str:
        rows = self.build_rows()
        if not rows:
            return "No jobs configured."

        header = f"{'ST':<3} {'JOB':<25} {'SCHEDULE':<20} {'LAST RUN':<22} {'NEXT RUN':<22} {'RUNS':>5}"
        sep = "-" * len(header)
        lines = [header, sep]

        for row in rows:
            last_run_str = row.last_run.strftime("%Y-%m-%d %H:%M:%S") if row.last_run else "never"
            next_run_str = row.next_run.strftime("%Y-%m-%d %H:%M:%S") if row.next_run else "unknown"
            lines.append(
                f"{row.status_symbol():<3} {row.name:<25} {row.schedule:<20} "
                f"{last_run_str:<22} {next_run_str:<22} {row.run_count:>5}"
            )

        lines.append(sep)
        lines.append(f"Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        return "\n".join(lines)

    def print(self) -> None:
        print(self.render())
