import pytest
from unittest.mock import MagicMock, patch

from cronwatcher.config import JobConfig
from cronwatcher.scheduler import Scheduler
from cronwatcher.runner import JobRunner


@pytest.fixture
def sample_job():
    return JobConfig(name="test_job", command="echo hello", schedule="* * * * *", timeout=30)


@pytest.fixture
def failing_job():
    return JobConfig(name="fail_job", command="exit 1", schedule="* * * * *", timeout=30)


@pytest.fixture
def scheduler(sample_job, failing_job):
    return Scheduler(jobs=[sample_job, failing_job])


@pytest.fixture
def runner(scheduler):
    return JobRunner(scheduler=scheduler)


def test_successful_job_returns_true(runner, sample_job):
    result = runner.run_job(sample_job)
    assert result is True


def test_successful_job_records_run(runner, scheduler, sample_job):
    runner.run_job(sample_job)
    status = scheduler.get_status(sample_job.name)
    assert status.last_run is not None
    assert status.last_success is not None
    assert status.consecutive_failures == 0


def test_failed_job_returns_false(runner, failing_job):
    result = runner.run_job(failing_job)
    assert result is False


def test_failed_job_records_failure(runner, scheduler, failing_job):
    runner.run_job(failing_job)
    status = scheduler.get_status(failing_job.name)
    assert status.consecutive_failures == 1


def test_failed_job_notifies(scheduler, failing_job):
    mock_notifier = MagicMock()
    runner = JobRunner(scheduler=scheduler, notifier=mock_notifier)
    runner.run_job(failing_job)
    mock_notifier.notify_failure.assert_called_once()
    call_args = mock_notifier.notify_failure.call_args[0]
    assert call_args[0] == failing_job.name


def test_timeout_triggers_failure_and_notify(scheduler, sample_job):
    mock_notifier = MagicMock()
    runner = JobRunner(scheduler=scheduler, notifier=mock_notifier)
    with patch("subprocess.run", side_effect=__import__("subprocess").TimeoutExpired(cmd="echo", timeout=1)):
        result = runner.run_job(sample_job)
    assert result is False
    mock_notifier.notify_failure.assert_called_once()
    status = scheduler.get_status(sample_job.name)
    assert status.consecutive_failures == 1


def test_no_notifier_does_not_raise_on_failure(scheduler, failing_job):
    runner = JobRunner(scheduler=scheduler, notifier=None)
    result = runner.run_job(failing_job)
    assert result is False
