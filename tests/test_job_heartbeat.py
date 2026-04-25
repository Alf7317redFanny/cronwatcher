"""Tests for cronwatcher/job_heartbeat.py"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cronwatcher.job_heartbeat import HeartbeatIndex, HeartbeatRecord


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "heartbeats.json"


@pytest.fixture
def index(state_file: Path) -> HeartbeatIndex:
    return HeartbeatIndex(state_file, default_interval=60)


def test_starts_empty(index: HeartbeatIndex) -> None:
    assert index.all() == []


def test_load_nonexistent_is_noop(tmp_path: Path) -> None:
    idx = HeartbeatIndex(tmp_path / "missing.json")
    assert idx.all() == []


def test_ping_returns_record(index: HeartbeatIndex) -> None:
    rec = index.ping("backup")
    assert isinstance(rec, HeartbeatRecord)
    assert rec.job_name == "backup"


def test_ping_persists_to_disk(index: HeartbeatIndex, state_file: Path) -> None:
    index.ping("backup")
    data = json.loads(state_file.read_text())
    assert len(data) == 1
    assert data[0]["job_name"] == "backup"


def test_get_returns_record(index: HeartbeatIndex) -> None:
    index.ping("cleanup")
    rec = index.get("cleanup")
    assert rec is not None
    assert rec.job_name == "cleanup"


def test_get_missing_returns_none(index: HeartbeatIndex) -> None:
    assert index.get("nonexistent") is None


def test_ping_uses_custom_interval(index: HeartbeatIndex) -> None:
    rec = index.ping("job", interval_seconds=120)
    assert rec.interval_seconds == 120


def test_ping_uses_default_interval(index: HeartbeatIndex) -> None:
    rec = index.ping("job")
    assert rec.interval_seconds == 60


def test_is_stale_when_overdue(index: HeartbeatIndex) -> None:
    rec = index.ping("old_job", interval_seconds=10)
    future = datetime.utcnow() + timedelta(seconds=20)
    assert rec.is_stale(now=future)


def test_is_not_stale_when_recent(index: HeartbeatIndex) -> None:
    rec = index.ping("fresh_job", interval_seconds=3600)
    assert not rec.is_stale()


def test_stale_jobs_returns_only_stale(index: HeartbeatIndex) -> None:
    index.ping("fresh", interval_seconds=3600)
    index.ping("stale", interval_seconds=1)
    future = datetime.utcnow() + timedelta(seconds=5)
    stale = index.stale_jobs(now=future)
    assert len(stale) == 1
    assert stale[0].job_name == "stale"


def test_roundtrip_via_reload(state_file: Path) -> None:
    idx1 = HeartbeatIndex(state_file, default_interval=60)
    idx1.ping("myjob", interval_seconds=300)
    idx2 = HeartbeatIndex(state_file, default_interval=60)
    rec = idx2.get("myjob")
    assert rec is not None
    assert rec.interval_seconds == 300


def test_repr_contains_job_name(index: HeartbeatIndex) -> None:
    rec = index.ping("myjob")
    assert "myjob" in repr(rec)
