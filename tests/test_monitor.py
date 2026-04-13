import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from cronwatcher.config import JobConfig
from cronwatcher.scheduler import Scheduler, JobStatus
from cronwatcher.notifier import Notifier, NotifierConfig
from cronwatcher.monitor import Monitor, MissedRun


@pytest.fixture
def sample_jobs():
    return [
        JobConfig(name="backup", schedule="0 2 * * *", command="/usr/bin/backup.sh"),
        JobConfig(name="cleanup", schedule="0 3 * * *", command="/usr/bin/cleanup.sh"),
    ]


@pytest.fixture
def scheduler(sample_jobs):
    return Scheduler(sample_jobs)


@pytest.fixture
def notifier():
    config = NotifierConfig(
        smtp_host="localhost",
        smtp_port=25,
        sender="alerts@example.com",
        recipients=["admin@example.com"],
    )
    return Notifier(config)


@pytest.fixture
def monitor(scheduler, notifier):
    return Monitor(scheduler, notifier)


def test_no_missed_runs_when_next_run_in_future(monitor, scheduler, sample_jobs):
    future = datetime.now(tz=timezone.utc) + timedelta(hours=1)
    for job in sample_jobs:
        scheduler.statuses[job.name].next_run = future

    missed = monitor.check_missed_runs(sample_jobs)
    assert missed == []


def test_detects_missed_run(monitor, scheduler, sample_jobs):
    past = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    scheduler.statuses["backup"].next_run = past
    future = datetime.now(tz=timezone.utc) + timedelta(hours=1)
    scheduler.statuses["cleanup"].next_run = future

    missed = monitor.check_missed_runs(sample_jobs)
    assert len(missed) == 1
    assert missed[0].job_name == "backup"


def test_missed_run_repr():
    now = datetime(2024, 1, 1, 2, 0, 0, tzinfo=timezone.utc)
    run = MissedRun(job_name="backup", expected_at=now, last_ran=None)
    assert "backup" in repr(run)
    assert "never" in repr(run)


def test_alert_missed_runs_sends_alerts(monitor, scheduler, sample_jobs):
    past = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    for job in sample_jobs:
        scheduler.statuses[job.name].next_run = past

    with patch.object(monitor.notifier, "send_alert") as mock_send:
        count = monitor.alert_missed_runs(sample_jobs)

    assert count == 2
    assert mock_send.call_count == 2


def test_alert_missed_runs_returns_zero_when_none(monitor, scheduler, sample_jobs):
    future = datetime.now(tz=timezone.utc) + timedelta(hours=2)
    for job in sample_jobs:
        scheduler.statuses[job.name].next_run = future

    with patch.object(monitor.notifier, "send_alert") as mock_send:
        count = monitor.alert_missed_runs(sample_jobs)

    assert count == 0
    mock_send.assert_not_called()


def test_check_missed_runs_skips_unknown_job(monitor, sample_jobs):
    unknown_job = JobConfig(name="ghost", schedule="* * * * *", command="/bin/ghost")
    missed = monitor.check_missed_runs([unknown_job])
    assert missed == []
