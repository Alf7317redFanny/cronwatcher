import pytest
from datetime import datetime, timezone, timedelta

from cronwatcher.config import JobConfig
from cronwatcher.scheduler import Scheduler, JobStatus


@pytest.fixture
def sample_jobs():
    return [
        JobConfig(name="backup", schedule="0 * * * *", command="/usr/bin/backup.sh"),
        JobConfig(name="cleanup", schedule="30 2 * * *", command="/usr/bin/cleanup.sh"),
    ]


@pytest.fixture
def scheduler(sample_jobs):
    return Scheduler(sample_jobs)


def test_scheduler_initializes_statuses(scheduler):
    assert "backup" in scheduler.statuses
    assert "cleanup" in scheduler.statuses
    assert isinstance(scheduler.statuses["backup"], JobStatus)


def test_record_successful_run(scheduler):
    scheduler.record_run("backup", success=True)
    status = scheduler.get_status("backup")
    assert status.last_run is not None
    assert status.failed is False
    assert status.missed is False
    assert status.next_expected is not None


def test_record_failed_run(scheduler):
    scheduler.record_run("backup", success=False, reason="exit code 1")
    status = scheduler.get_status("backup")
    assert status.failed is True
    assert status.failure_reason == "exit code 1"


def test_record_failed_run_default_reason(scheduler):
    scheduler.record_run("backup", success=False)
    status = scheduler.get_status("backup")
    assert status.failure_reason == "unknown error"


def test_record_run_unknown_job_raises(scheduler):
    with pytest.raises(KeyError, match="ghost"):
        scheduler.record_run("ghost")


def test_get_status_unknown_job_raises(scheduler):
    with pytest.raises(KeyError, match="nope"):
        scheduler.get_status("nope")


def test_check_missed_detects_overdue(scheduler):
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    scheduler.statuses["backup"].next_expected = datetime.now(timezone.utc) - timedelta(minutes=5)
    missed = scheduler.check_missed(now=future)
    assert "backup" in missed
    assert scheduler.statuses["backup"].missed is True


def test_check_missed_not_overdue(scheduler):
    scheduler.statuses["backup"].next_expected = datetime.now(timezone.utc) + timedelta(hours=1)
    missed = scheduler.check_missed()
    assert "backup" not in missed


def test_compute_next_expected_returns_future(scheduler):
    nxt = scheduler.compute_next_expected("backup")
    assert nxt is not None
    assert nxt > datetime.now(timezone.utc)


def test_compute_next_expected_unknown_job(scheduler):
    result = scheduler.compute_next_expected("nonexistent")
    assert result is None
