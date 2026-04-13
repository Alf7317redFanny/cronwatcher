"""Tests for cronwatcher.retention."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cronwatcher.history import History, RunRecord
from cronwatcher.retention import RetentionManager, RetentionPolicy


@pytest.fixture()
def tmp_history_path(tmp_path: Path) -> Path:
    return tmp_path / "history.json"


@pytest.fixture()
def history(tmp_history_path: Path) -> History:
    h = History(path=tmp_history_path)
    h.load()
    return h


def _record(job_name: str, days_ago: float, success: bool = True) -> RunRecord:
    ts = datetime.utcnow() - timedelta(days=days_ago)
    return RunRecord(job_name=job_name, timestamp=ts, success=success, output="")


def test_policy_defaults() -> None:
    policy = RetentionPolicy()
    assert policy.max_age_days == 30
    assert policy.max_records_per_job == 100


def test_policy_invalid_age_raises() -> None:
    with pytest.raises(ValueError, match="max_age_days"):
        RetentionPolicy(max_age_days=0)


def test_policy_invalid_records_raises() -> None:
    with pytest.raises(ValueError, match="max_records_per_job"):
        RetentionPolicy(max_records_per_job=-1)


def test_prune_removes_old_records(history: History) -> None:
    history.records = [
        _record("job_a", days_ago=5),
        _record("job_a", days_ago=40),  # too old
        _record("job_a", days_ago=35),  # too old
    ]
    manager = RetentionManager(history, RetentionPolicy(max_age_days=30))
    removed = manager.prune()
    assert removed == 2
    assert len(history.records) == 1


def test_prune_caps_records_per_job(history: History) -> None:
    history.records = [_record("job_b", days_ago=i) for i in range(10)]
    policy = RetentionPolicy(max_age_days=30, max_records_per_job=5)
    manager = RetentionManager(history, policy)
    removed = manager.prune()
    assert removed == 5
    assert len(history.records) == 5


def test_prune_keeps_newest_records(history: History) -> None:
    history.records = [_record("job_c", days_ago=i) for i in range(6)]
    policy = RetentionPolicy(max_age_days=30, max_records_per_job=3)
    manager = RetentionManager(history, policy)
    manager.prune()
    ages = [(datetime.utcnow() - r.timestamp).days for r in history.records]
    assert max(ages) <= 3


def test_prune_persists_changes(history: History, tmp_history_path: Path) -> None:
    history.records = [
        _record("job_d", days_ago=2),
        _record("job_d", days_ago=60),
    ]
    manager = RetentionManager(history, RetentionPolicy(max_age_days=30))
    manager.prune()
    data = json.loads(tmp_history_path.read_text())
    assert len(data) == 1


def test_prune_returns_zero_when_nothing_removed(history: History) -> None:
    history.records = [_record("job_e", days_ago=1)]
    manager = RetentionManager(history, RetentionPolicy())
    removed = manager.prune()
    assert removed == 0
