"""Tests for the dashboard module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.dashboard import Dashboard, JobRow
from cronwatcher.history import History, RunRecord
from cronwatcher.scheduler import JobStatus, Scheduler


@pytest.fixture
def sample_jobs():
    return [
        JobConfig(name="backup", schedule="0 2 * * *", command="tar -czf /tmp/b.tar.gz /data"),
        JobConfig(name="cleanup", schedule="0 3 * * *", command="rm -rf /tmp/old"),
    ]


@pytest.fixture
def scheduler(sample_jobs):
    return Scheduler(sample_jobs)


@pytest.fixture
def history(tmp_path):
    h = History(path=tmp_path / "history.json")
    h.load()
    return h


@pytest.fixture
def dashboard(scheduler, history):
    return Dashboard(scheduler=scheduler, history=history)


def test_build_rows_returns_one_per_job(dashboard, sample_jobs):
    rows = dashboard.build_rows()
    assert len(rows) == len(sample_jobs)


def test_row_last_run_none_when_no_history(dashboard):
    rows = dashboard.build_rows()
    for row in rows:
        assert row.last_run is None
        assert row.last_status is None
        assert row.run_count == 0


def test_row_reflects_history(dashboard, history):
    ran_at = datetime(2024, 6, 1, 2, 0, 0)
    record = RunRecord(job_name="backup", ran_at=ran_at, status="success", output="ok", duration=1.2)
    history.add(record)

    rows = dashboard.build_rows()
    backup_row = next(r for r in rows if r.name == "backup")
    assert backup_row.last_run == ran_at
    assert backup_row.last_status == "success"
    assert backup_row.run_count == 1


def test_row_reflects_most_recent_run(dashboard, history):
    """When multiple runs exist, the row should reflect the most recent one."""
    first_run = datetime(2024, 6, 1, 2, 0, 0)
    second_run = datetime(2024, 6, 2, 2, 0, 0)
    history.add(RunRecord(job_name="backup", ran_at=first_run, status="failure", output="err", duration=0.5))
    history.add(RunRecord(job_name="backup", ran_at=second_run, status="success", output="ok", duration=1.2))

    rows = dashboard.build_rows()
    backup_row = next(r for r in rows if r.name == "backup")
    assert backup_row.last_run == second_run
    assert backup_row.last_status == "success"
    assert backup_row.run_count == 2


def test_status_symbol_success():
    row = JobRow(name="x", schedule="* * * * *", last_run=None, last_status="success", next_run=None, run_count=1)
    assert row.status_symbol() == "✓"


def test_status_symbol_failure():
    row = JobRow(name="x", schedule="* * * * *", last_run=None, last_status="failure", next_run=None, run_count=1)
    assert row.status_symbol() == "✗"


def test_status_symbol_unknown():
    row = JobRow(name="x", schedule="* * * * *", last_run=None, last_status=None, next_run=None, run_count=0)
    assert row.status_symbol() == "?"


def test_render_contains_job_names(dashboard):
    output = dashboard.render()
    assert "backup" in output
    assert "cleanup" in output


def test_render_no_jobs():
    empty_scheduler = Scheduler([])
    empty_history = MagicMock()
    empty_history.get.return_value = []
    d = Dashboard(scheduler=empty_scheduler, history=empty_history)
    assert d.render() == "No jobs configured."


def test_print_calls_render(dashboard, capsys):
    dashboard.print()
    captured = capsys.readouterr()
    assert "backup" in captured.out
