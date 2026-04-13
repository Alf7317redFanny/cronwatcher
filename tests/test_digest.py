"""Tests for cronwatcher.digest module."""

from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.digest import DigestBuilder, DigestEntry
from cronwatcher.history import History, RunRecord
from cronwatcher.scheduler import Scheduler


@pytest.fixture
def sample_jobs():
    return [
        JobConfig(name="backup", schedule="0 2 * * *", command="tar -czf /tmp/b.tgz /data"),
        JobConfig(name="sync", schedule="*/15 * * * *", command="rsync -a /src /dst"),
    ]


@pytest.fixture
def scheduler(sample_jobs):
    return Scheduler(sample_jobs)


@pytest.fixture
def history(tmp_path, sample_jobs):
    h = History(tmp_path / "hist.json")
    now = datetime.now(timezone.utc)
    h.add(RunRecord(job_name="backup", ran_at=now - timedelta(hours=2), success=True, duration=1.2))
    h.add(RunRecord(job_name="backup", ran_at=now - timedelta(hours=1), success=False, duration=0.5))
    h.add(RunRecord(job_name="sync", ran_at=now - timedelta(minutes=30), success=True, duration=0.1))
    h.add(RunRecord(job_name="sync", ran_at=now - timedelta(minutes=15), success=True, duration=0.1))
    return h


@pytest.fixture
def builder(history, scheduler):
    return DigestBuilder(history=history, scheduler=scheduler)


def test_build_returns_one_entry_per_job(builder, sample_jobs):
    entries = builder.build()
    assert len(entries) == len(sample_jobs)


def test_entry_counts_are_correct(builder):
    entries = {e.job_name: e for e in builder.build()}
    assert entries["backup"].total_runs == 2
    assert entries["backup"].failures == 1
    assert entries["sync"].total_runs == 2
    assert entries["sync"].failures == 0


def test_success_rate_calculation(builder):
    entries = {e.job_name: e for e in builder.build()}
    assert entries["backup"].success_rate == pytest.approx(0.5)
    assert entries["sync"].success_rate == pytest.approx(1.0)


def test_last_run_is_most_recent(builder, history):
    entries = {e.job_name: e for e in builder.build()}
    backup_records = [r for r in history.records if r.job_name == "backup"]
    expected = max(r.ran_at for r in backup_records)
    assert entries["backup"].last_run == expected


def test_since_filter_limits_records(builder):
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=60)
    entries = {e.job_name: e for e in builder.build(since=cutoff)}
    # Only the failure 1h ago is borderline; sync has 2 runs within window
    assert entries["sync"].total_runs == 2


def test_no_runs_gives_zero_success_rate(scheduler, tmp_path):
    h = History(tmp_path / "empty.json")
    b = DigestBuilder(history=h, scheduler=scheduler)
    entries = {e.job_name: e for e in b.build()}
    assert entries["backup"].success_rate == 0.0
    assert entries["backup"].last_run is None


def test_format_text_contains_job_names(builder):
    text = builder.format_text()
    assert "backup" in text
    assert "sync" in text


def test_format_text_contains_header(builder):
    text = builder.format_text()
    assert "CronWatcher Digest" in text


def test_digest_entry_repr():
    e = DigestEntry(job_name="test", total_runs=5, failures=1, last_run=None, success_rate=0.8)
    assert "test" in repr(e)
    assert "80.0%" in repr(e)
