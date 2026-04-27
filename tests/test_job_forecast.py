"""Tests for cronwatcher.job_forecast and forecast_cli."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.job_forecast import ForecastEntry, JobForecaster
from cronwatcher.forecast_cli import (
    add_forecast_args,
    forecast_summary,
    run_forecast_cmd,
)


def _make_job(name: str, schedule: str = "0 * * * *") -> JobConfig:
    return JobConfig(name=name, command=f"echo {name}", schedule=schedule)


@pytest.fixture
def jobs():
    return [
        _make_job("hourly", "0 * * * *"),
        _make_job("daily", "0 9 * * *"),
    ]


@pytest.fixture
def forecaster(jobs):
    return JobForecaster(jobs, count=3)


def test_forecast_returns_one_entry_per_job(forecaster, jobs):
    entries = forecaster.forecast()
    assert len(entries) == len(jobs)


def test_forecast_entry_names_match_jobs(forecaster, jobs):
    entries = forecaster.forecast()
    names = [e.job_name for e in entries]
    assert names == [j.name for j in jobs]


def test_forecast_returns_correct_count(forecaster):
    entries = forecaster.forecast()
    for entry in entries:
        assert len(entry.next_runs) == 3


def test_forecast_runs_are_in_future(forecaster):
    base = datetime(2024, 1, 1, 12, 0, 0)
    entries = forecaster.forecast(base=base)
    for entry in entries:
        for run in entry.next_runs:
            assert run > base


def test_forecast_runs_are_ascending(forecaster):
    entries = forecaster.forecast()
    for entry in entries:
        assert entry.next_runs == sorted(entry.next_runs)


def test_invalid_count_raises():
    with pytest.raises(ValueError, match="count must be at least 1"):
        JobForecaster([], count=0)


def test_invalid_schedule_yields_empty_runs():
    bad_job = _make_job("broken", "not-a-cron")
    f = JobForecaster([bad_job], count=3)
    entries = f.forecast()
    assert entries[0].next_runs == []


def test_next_run_returns_datetime(jobs):
    f = JobForecaster(jobs)
    result = f.next_run(jobs[0])
    assert isinstance(result, datetime)


def test_next_run_returns_none_on_bad_schedule():
    bad = _make_job("bad", "not-a-cron")
    f = JobForecaster([bad])
    assert f.next_run(bad) is None


def test_forecast_entry_repr():
    dt = datetime(2024, 6, 1, 9, 0)
    entry = ForecastEntry(job_name="myjob", next_runs=[dt])
    assert "myjob" in repr(entry)
    assert "2024-06-01 09:00" in repr(entry)


def test_forecast_entry_to_dict():
    dt = datetime(2024, 6, 1, 9, 0)
    entry = ForecastEntry(job_name="myjob", next_runs=[dt])
    d = entry.to_dict()
    assert d["job_name"] == "myjob"
    assert len(d["next_runs"]) == 1


def test_add_forecast_args_registers_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_forecast_args(sub)
    args = parser.parse_args(["forecast", "--count", "3"])
    assert args.count == 3


def test_run_forecast_cmd_missing_job_returns_one(jobs):
    args = argparse.Namespace(job="nonexistent", count=3)
    rc = run_forecast_cmd(args, jobs)
    assert rc == 1


def test_run_forecast_cmd_success(jobs, capsys):
    args = argparse.Namespace(job=None, count=2)
    rc = run_forecast_cmd(args, jobs)
    assert rc == 0
    out = capsys.readouterr().out
    assert "hourly" in out
    assert "daily" in out


def test_forecast_summary_shows_soonest():
    base = datetime(2024, 1, 1, 12, 0, 0)
    dt1 = datetime(2024, 1, 1, 13, 0, 0)
    dt2 = datetime(2024, 1, 1, 14, 0, 0)
    entries = [
        ForecastEntry("job-a", [dt1]),
        ForecastEntry("job-b", [dt2]),
    ]
    summary = forecast_summary(entries, now=base)
    assert "job-a" in summary
    assert "60 min" in summary


def test_forecast_summary_no_entries():
    summary = forecast_summary([])
    assert "No upcoming" in summary
