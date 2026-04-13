"""Runs individual cron jobs as subprocesses and records outcomes."""

from __future__ import annotations

import subprocess
from typing import Optional

from cronwatcher.config import JobConfig
from cronwatcher.history import History, make_record
from cronwatcher.scheduler import Scheduler


class JobRunner:
    def __init__(
        self,
        scheduler: Scheduler,
        history: Optional[History] = None,
        timeout: int = 3600,
    ) -> None:
        self.scheduler = scheduler
        self.history = history
        self.timeout = timeout

    def run_job(self, job: JobConfig) -> bool:
        """Execute a job command, update scheduler state, and record history.

        Returns True on success, False on failure.
        """
        try:
            result = subprocess.run(
                job.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            success = result.returncode == 0
        except subprocess.TimeoutExpired:
            self._record(
                job.name,
                success=False,
                exit_code=None,
                error_message=f"Job '{job.name}' timed out after {self.timeout}s",
            )
            self.scheduler.mark_failed(job.name)
            return False
        except Exception as exc:  # pragma: no cover
            self._record(job.name, success=False, error_message=str(exc))
            self.scheduler.mark_failed(job.name)
            return False

        if success:
            self.scheduler.mark_ran(job.name)
            self._record(job.name, success=True, exit_code=result.returncode)
        else:
            self.scheduler.mark_failed(job.name)
            stderr = result.stderr.strip() or None
            self._record(
                job.name,
                success=False,
                exit_code=result.returncode,
                error_message=stderr,
            )

        return success

    def _record(
        self,
        job_name: str,
        *,
        success: bool,
        exit_code: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        if self.history is None:
            return
        self.history.add(
            make_record(
                job_name,
                success=success,
                exit_code=exit_code,
                error_message=error_message,
            )
        )
