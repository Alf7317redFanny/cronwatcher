"""Tests for cronwatcher.alerting module."""

import json
import time
from pathlib import Path

import pytest

from cronwatcher.alerting import AlertRecord, AlertThrottle


@pytest.fixture
def throttle():
    return AlertThrottle(cooldown_seconds=60)


@pytest.fixture
def state_file(tmp_path):
    return tmp_path / "alert_state.json"


def test_should_alert_when_no_record(throttle):
    assert throttle.should_alert("backup") is True


def test_should_not_alert_within_cooldown(throttle):
    throttle.record_alert("backup")
    assert throttle.should_alert("backup") is False


def test_should_alert_after_cooldown(throttle):
    throttle.record_alert("backup")
    throttle._records["backup"].last_sent -= 120  # push back in time
    assert throttle.should_alert("backup") is True


def test_record_alert_increments_count(throttle):
    throttle.record_alert("backup")
    throttle.record_alert("backup")
    assert throttle._records["backup"].count == 2


def test_reset_clears_record(throttle):
    throttle.record_alert("backup")
    throttle.reset("backup")
    assert "backup" not in throttle._records
    assert throttle.should_alert("backup") is True


def test_reset_nonexistent_job_is_noop(throttle):
    throttle.reset("ghost_job")  # should not raise


def test_state_persisted_to_disk(state_file):
    t = AlertThrottle(cooldown_seconds=60, state_path=state_file)
    t.record_alert("nightly")
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert "nightly" in data
    assert data["nightly"]["count"] == 1


def test_state_loaded_from_disk(state_file):
    t1 = AlertThrottle(cooldown_seconds=60, state_path=state_file)
    t1.record_alert("nightly")

    t2 = AlertThrottle(cooldown_seconds=60, state_path=state_file)
    assert "nightly" in t2._records
    assert t2._records["nightly"].count == 1
    assert t2.should_alert("nightly") is False


def test_alert_record_repr():
    rec = AlertRecord(job_name="sync", last_sent=1700000000.0, count=3)
    assert "sync" in repr(rec)
    assert "3" in repr(rec)


def test_multiple_jobs_tracked_independently(throttle):
    throttle.record_alert("job_a")
    assert throttle.should_alert("job_a") is False
    assert throttle.should_alert("job_b") is True
