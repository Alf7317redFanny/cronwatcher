import pytest
from cronwatcher.job_retry import RetryPolicy, RetryManager


@pytest.fixture
def policy() -> RetryPolicy:
    return RetryPolicy(max_attempts=3, delay_seconds=2.0)


@pytest.fixture
def manager(policy: RetryPolicy) -> RetryManager:
    return RetryManager(policy)


def test_policy_defaults():
    p = RetryPolicy()
    assert p.max_attempts == 3
    assert p.delay_seconds == 5.0


def test_policy_invalid_max_attempts_raises():
    with pytest.raises(ValueError, match="max_attempts"):
        RetryPolicy(max_attempts=0)


def test_policy_invalid_delay_raises():
    with pytest.raises(ValueError, match="delay_seconds"):
        RetryPolicy(delay_seconds=-1)


def test_policy_per_job_invalid_raises():
    with pytest.raises(ValueError, match="per_job"):
        RetryPolicy(per_job={"backup": 0})


def test_attempts_for_uses_per_job_override():
    p = RetryPolicy(max_attempts=3, per_job={"backup": 5})
    assert p.attempts_for("backup") == 5
    assert p.attempts_for("other") == 3


def test_should_retry_initially_true(manager):
    assert manager.should_retry("myjob") is True


def test_record_attempt_increments(manager):
    manager.record_attempt("myjob", error="timeout")
    assert manager.attempt_count("myjob") == 1


def test_should_not_retry_after_max(manager):
    for _ in range(3):
        manager.record_attempt("myjob")
    assert manager.should_retry("myjob") is False


def test_record_attempt_stores_error(manager):
    state = manager.record_attempt("myjob", error="exit code 1")
    assert state.last_error == "exit code 1"


def test_reset_clears_state(manager):
    manager.record_attempt("myjob")
    manager.reset("myjob")
    assert manager.attempt_count("myjob") == 0


def test_delay_for_returns_policy_delay(manager):
    assert manager.delay_for("anyjob") == 2.0


def test_repr_of_state(manager):
    state = manager.record_attempt("myjob", error="oops")
    assert "myjob" in repr(state)
    assert "oops" in repr(state)
