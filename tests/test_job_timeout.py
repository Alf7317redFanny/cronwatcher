"""Tests for cronwatcher.job_timeout."""
import pytest
from cronwatcher.job_timeout import TimeoutConfig, TimeoutTracker, TimeoutViolation


# ---------------------------------------------------------------------------
# TimeoutConfig
# ---------------------------------------------------------------------------

def test_default_seconds_used_when_no_override():
    cfg = TimeoutConfig(default_seconds=60)
    assert cfg.for_job("backup") == 60


def test_per_job_override_takes_precedence():
    cfg = TimeoutConfig(default_seconds=60, per_job={"backup": 120})
    assert cfg.for_job("backup") == 120
    assert cfg.for_job("sync") == 60


def test_invalid_default_raises():
    with pytest.raises(ValueError, match="default_seconds"):
        TimeoutConfig(default_seconds=0)


def test_invalid_per_job_raises():
    with pytest.raises(ValueError, match="backup"):
        TimeoutConfig(default_seconds=60, per_job={"backup": -5})


# ---------------------------------------------------------------------------
# TimeoutTracker.check
# ---------------------------------------------------------------------------

@pytest.fixture
def tracker():
    cfg = TimeoutConfig(default_seconds=30, per_job={"slow_job": 120})
    return TimeoutTracker(cfg)


def test_no_violation_within_limit(tracker):
    result = tracker.check("any_job", 29.9)
    assert result is None


def test_violation_returned_when_exceeded(tracker):
    result = tracker.check("any_job", 31.0)
    assert isinstance(result, TimeoutViolation)
    assert result.job_name == "any_job"
    assert result.allowed_seconds == 30
    assert result.actual_seconds == pytest.approx(31.0)


def test_per_job_limit_respected(tracker):
    # slow_job has a 120-second limit
    assert tracker.check("slow_job", 119.0) is None
    v = tracker.check("slow_job", 121.0)
    assert v is not None
    assert v.allowed_seconds == 120


def test_exact_limit_is_not_a_violation(tracker):
    assert tracker.check("any_job", 30.0) is None


# ---------------------------------------------------------------------------
# TimeoutTracker.check_many
# ---------------------------------------------------------------------------

def test_check_many_returns_only_violations(tracker):
    runtimes = {"any_job": 10.0, "slow_job": 200.0, "other": 5.0}
    violations = tracker.check_many(runtimes)
    assert len(violations) == 1
    assert violations[0].job_name == "slow_job"


def test_check_many_empty_input(tracker):
    assert tracker.check_many({}) == []


def test_check_many_all_ok(tracker):
    runtimes = {"any_job": 1.0, "slow_job": 1.0}
    assert tracker.check_many(runtimes) == []


def test_check_many_all_violated(tracker):
    runtimes = {"any_job": 999.0, "slow_job": 999.0}
    violations = tracker.check_many(runtimes)
    assert len(violations) == 2
    names = {v.job_name for v in violations}
    assert names == {"any_job", "slow_job"}
