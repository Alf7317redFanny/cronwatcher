import subprocess
import logging
from datetime import datetime
from typing import Optional

from cronwatcher.config import JobConfig
from cronwatcher.scheduler import Scheduler
from cronwatcher.notifier import Notifier

logger = logging.getLogger(__name__)


class JobRunner:
    def __init__(self, scheduler: Scheduler, notifier: Optional[Notifier] = None):
        self.scheduler = scheduler
        self.notifier = notifier

    def run_job(self, job: JobConfig) -> bool:
        """
        Execute a cron job command and record the result.
        Returns True if the job succeeded, False otherwise.
        """
        logger.info(f"Running job '{job.name}': {job.command}")
        start_time = datetime.utcnow()

        try:
            result = subprocess.run(
                job.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=job.timeout,
            )

            duration = (datetime.utcnow() - start_time).total_seconds()

            if result.returncode == 0:
                logger.info(f"Job '{job.name}' succeeded in {duration:.2f}s")
                self.scheduler.record_run(job.name, success=True)
                return True
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"Job '{job.name}' failed (exit {result.returncode}): {error_msg}")
                self.scheduler.record_run(job.name, success=False)
                if self.notifier:
                    self.notifier.notify_failure(job.name, error_msg)
                return False

        except subprocess.TimeoutExpired:
            msg = f"Job '{job.name}' timed out after {job.timeout}s"
            logger.error(msg)
            self.scheduler.record_run(job.name, success=False)
            if self.notifier:
                self.notifier.notify_failure(job.name, msg)
            return False

        except Exception as exc:
            msg = f"Unexpected error running job '{job.name}': {exc}"
            logger.exception(msg)
            self.scheduler.record_run(job.name, success=False)
            if self.notifier:
                self.notifier.notify_failure(job.name, str(exc))
            return False
