"""Tests for cronwatcher/audit.py"""

import json
import pytest
from pathlib import Path

from cronwatcher.audit import AuditEvent, AuditLog


@pytest.fixture
def audit_path(tmp_path) -> str:
    return str(tmp_path / "audit.log")


@pytest.fixture
def audit(audit_path) -> AuditLog:
    return AuditLog(audit_path)


def test_starts_empty(audit):
    assert audit.events() == []


def test_record_returns_event(audit):
    event = audit.record("job_started", "job backup started", job_name="backup")
    assert isinstance(event, AuditEvent)
    assert event.event_type == "job_started"
    assert event.job_name == "backup"
    assert event.detail == "job backup started"


def test_record_persists_to_disk(audit, audit_path):
    audit.record("job_failed", "exit code 1", job_name="cleanup")
    lines = Path(audit_path).read_text().strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["event_type"] == "job_failed"
    assert data["job_name"] == "cleanup"


def test_multiple_events_appended(audit, audit_path):
    audit.record("job_started", "start", job_name="sync")
    audit.record("job_finished", "done", job_name="sync")
    lines = Path(audit_path).read_text().strip().splitlines()
    assert len(lines) == 2


def test_load_existing_file(audit_path):
    log1 = AuditLog(audit_path)
    log1.record("alert_sent", "email dispatched", job_name="report")
    log1.record("job_missed", "missed window", job_name="report")

    log2 = AuditLog(audit_path)
    assert len(log2.events()) == 2


def test_load_nonexistent_file_is_noop(tmp_path):
    log = AuditLog(str(tmp_path / "missing.log"))
    assert log.events() == []


def test_filter_by_event_type(audit):
    audit.record("job_started", "s", job_name="a")
    audit.record("job_failed", "f", job_name="b")
    audit.record("job_started", "s2", job_name="c")
    started = audit.events(event_type="job_started")
    assert len(started) == 2
    assert all(e.event_type == "job_started" for e in started)


def test_filter_by_job_name(audit):
    audit.record("job_started", "s", job_name="alpha")
    audit.record("job_failed", "f", job_name="beta")
    audit.record("job_finished", "done", job_name="alpha")
    alpha = audit.events(job_name="alpha")
    assert len(alpha) == 2
    assert all(e.job_name == "alpha" for e in alpha)


def test_event_without_job_name(audit):
    event = audit.record("system_start", "cronwatcher started")
    assert event.job_name is None
    loaded = AuditLog(audit.path)
    assert loaded.events()[0].job_name is None


def test_clear_removes_events_and_file(audit, audit_path):
    audit.record("job_started", "x", job_name="z")
    audit.clear()
    assert audit.events() == []
    assert not Path(audit_path).exists()


def test_repr(audit):
    event = audit.record("job_missed", "missed", job_name="nightly")
    assert "job_missed" in repr(event)
    assert "nightly" in repr(event)
