"""Tests for cronwatcher.history module."""

import json
import os
import tempfile
import time

import pytest

from cronwatcher.history import History, RunRecord, make_record


@pytest.fixture
def tmp_history_path(tmp_path):
    return str(tmp_path / "history.json")


@pytest.fixture
def history(tmp_history_path):
    return History(path=tmp_history_path)


def test_history_starts_empty(history):
    assert history.records == []


def test_load_nonexistent_file_is_noop(history):
    history.load()  # should not raise
    assert history.records == []


def test_add_persists_to_disk(history, tmp_history_path):
    record = make_record("backup", success=True, exit_code=0)
    history.add(record)

    assert os.path.exists(tmp_history_path)
    with open(tmp_history_path) as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["job_name"] == "backup"
    assert data[0]["success"] is True


def test_load_reads_persisted_records(history, tmp_history_path):
    record = make_record("cleanup", success=False, exit_code=1, error_message="oops")
    history.add(record)

    fresh = History(path=tmp_history_path)
    fresh.load()
    assert len(fresh.records) == 1
    assert fresh.records[0].job_name == "cleanup"
    assert fresh.records[0].success is False
    assert fresh.records[0].error_message == "oops"


def test_for_job_filters_correctly(history):
    history.add(make_record("job_a", success=True))
    history.add(make_record("job_b", success=False))
    history.add(make_record("job_a", success=False))

    job_a_records = history.for_job("job_a")
    assert len(job_a_records) == 2
    assert all(r.job_name == "job_a" for r in job_a_records)


def test_for_job_returns_newest_first(history):
    history.add(make_record("job_a", success=True))
    time.sleep(0.01)
    history.add(make_record("job_a", success=False))

    records = history.for_job("job_a")
    assert records[0].ran_at >= records[1].ran_at


def test_last_run_returns_most_recent(history):
    history.add(make_record("myjob", success=True))
    time.sleep(0.01)
    history.add(make_record("myjob", success=False, exit_code=2))

    last = history.last_run("myjob")
    assert last is not None
    assert last.success is False


def test_last_run_returns_none_for_unknown_job(history):
    assert history.last_run("ghost_job") is None


def test_multiple_adds_accumulate(history, tmp_history_path):
    """Ensure successive adds append records rather than overwriting."""
    history.add(make_record("job_x", success=True))
    history.add(make_record("job_x", success=False))
    history.add(make_record("job_y", success=True))

    with open(tmp_history_path) as f:
        data = json.load(f)
    assert len(data) == 3
    assert len(history.records) == 3


def test_run_record_repr():
    r = RunRecord(job_name="test", ran_at="2024-01-01T00:00:00", success=True)
    assert "OK" in repr(r)
    r2 = RunRecord(job_name="test", ran_at="2024-01-01T00:00:00", success=False)
    assert "FAIL" in repr(r2)
