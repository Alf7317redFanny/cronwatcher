"""Tests for cronwatcher/job_sla.py"""
import json
import pytest
from pathlib import Path
from cronwatcher.job_sla import SLAPolicy, SLAViolation, SLATracker


# ---------------------------------------------------------------------------
# SLAPolicy
# ---------------------------------------------------------------------------

def test_policy_defaults():
    p = SLAPolicy()
    assert p.max_duration_seconds == 3600.0
    assert p.min_success_rate == 0.95


def test_policy_per_job_override():
    p = SLAPolicy(max_duration_seconds=60.0, per_job={"backup": 120.0})
    assert p.max_duration_for("backup") == 120.0
    assert p.max_duration_for("other") == 60.0


def test_policy_invalid_duration_raises():
    with pytest.raises(ValueError, match="max_duration_seconds"):
        SLAPolicy(max_duration_seconds=-1)


def test_policy_invalid_success_rate_raises():
    with pytest.raises(ValueError, match="min_success_rate"):
        SLAPolicy(min_success_rate=1.5)


def test_policy_zero_success_rate_allowed():
    p = SLAPolicy(min_success_rate=0.0)
    assert p.min_success_rate == 0.0


# ---------------------------------------------------------------------------
# SLAViolation
# ---------------------------------------------------------------------------

def test_violation_repr():
    v = SLAViolation(job_name="myjob", violation_type="duration", detail="too slow")
    assert "myjob" in repr(v)
    assert "duration" in repr(v)


def test_violation_roundtrip():
    v = SLAViolation(job_name="myjob", violation_type="success_rate", detail="low rate")
    d = v.to_dict()
    v2 = SLAViolation.from_dict(d)
    assert v2.job_name == v.job_name
    assert v2.violation_type == v.violation_type
    assert v2.detail == v.detail
    assert v2.timestamp == v.timestamp


# ---------------------------------------------------------------------------
# SLATracker fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def state_file(tmp_path):
    return tmp_path / "sla_state.json"


@pytest.fixture
def policy():
    return SLAPolicy(max_duration_seconds=30.0, min_success_rate=0.8)


@pytest.fixture
def tracker(state_file, policy):
    return SLATracker(state_file=state_file, policy=policy)


# ---------------------------------------------------------------------------
# SLATracker tests
# ---------------------------------------------------------------------------

def test_starts_empty(tracker):
    assert tracker.all_violations() == []


def test_check_duration_no_violation(tracker):
    result = tracker.check_duration("job_a", 10.0)
    assert result is None
    assert tracker.all_violations() == []


def test_check_duration_violation(tracker):
    v = tracker.check_duration("job_a", 60.0)
    assert v is not None
    assert v.violation_type == "duration"
    assert "job_a" in v.detail


def test_check_success_rate_no_violation(tracker):
    result = tracker.check_success_rate("job_b", 0.9)
    assert result is None


def test_check_success_rate_violation(tracker):
    v = tracker.check_success_rate("job_b", 0.5)
    assert v is not None
    assert v.violation_type == "success_rate"


def test_violations_for_filters_by_job(tracker):
    tracker.check_duration("job_a", 999.0)
    tracker.check_success_rate("job_b", 0.1)
    assert len(tracker.violations_for("job_a")) == 1
    assert len(tracker.violations_for("job_b")) == 1
    assert tracker.violations_for("job_c") == []


def test_violations_persisted_to_disk(state_file, policy):
    t = SLATracker(state_file=state_file, policy=policy)
    t.check_duration("job_x", 9999.0)
    t2 = SLATracker(state_file=state_file, policy=policy)
    assert len(t2.all_violations()) == 1
    assert t2.all_violations()[0].job_name == "job_x"


def test_load_nonexistent_file_is_noop(tmp_path, policy):
    t = SLATracker(state_file=tmp_path / "missing.json", policy=policy)
    assert t.all_violations() == []


def test_clear_specific_job(tracker):
    tracker.check_duration("job_a", 999.0)
    tracker.check_duration("job_b", 999.0)
    tracker.clear("job_a")
    assert tracker.violations_for("job_a") == []
    assert len(tracker.violations_for("job_b")) == 1


def test_clear_all(tracker):
    tracker.check_duration("job_a", 999.0)
    tracker.check_success_rate("job_b", 0.0)
    tracker.clear()
    assert tracker.all_violations() == []
