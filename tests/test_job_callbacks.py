"""Tests for cronwatcher.job_callbacks."""
import pytest

from cronwatcher.config import JobConfig
from cronwatcher.job_callbacks import CallbackEvent, CallbackRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_job(name: str = "backup") -> JobConfig:
    return JobConfig(name=name, schedule="@daily", command="echo hi")


@pytest.fixture
def registry() -> CallbackRegistry:
    return CallbackRegistry()


# ---------------------------------------------------------------------------
# CallbackEvent
# ---------------------------------------------------------------------------

def test_callback_event_repr_no_error():
    ev = CallbackEvent(job_name="sync", event="on_success")
    assert "sync" in repr(ev)
    assert "on_success" in repr(ev)
    assert "error" not in repr(ev)


def test_callback_event_repr_with_error():
    ev = CallbackEvent(job_name="sync", event="on_failure", error="boom")
    assert "boom" in repr(ev)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def test_register_valid_event(registry):
    registry.register("on_start", lambda j, c: None)
    assert registry.count("on_start") == 1


def test_register_invalid_event_raises(registry):
    with pytest.raises(ValueError, match="Unknown event"):
        registry.register("on_timeout", lambda j, c: None)


def test_register_multiple_callbacks(registry):
    registry.register("on_success", lambda j, c: None)
    registry.register("on_success", lambda j, c: None)
    assert registry.count("on_success") == 2


# ---------------------------------------------------------------------------
# Firing
# ---------------------------------------------------------------------------

def test_fire_calls_callback(registry):
    called = []
    registry.register("on_start", lambda j, c: called.append(j.name))
    job = _make_job()
    registry.fire("on_start", job)
    assert called == ["backup"]


def test_fire_passes_context(registry):
    received = {}
    registry.register("on_success", lambda j, c: received.update(c))
    job = _make_job()
    registry.fire("on_success", job, context={"exit_code": 0})
    assert received["exit_code"] == 0


def test_fire_captures_callback_error(registry):
    def bad(j, c):
        raise RuntimeError("oops")

    registry.register("on_failure", bad)
    job = _make_job()
    results = registry.fire("on_failure", job)
    assert len(results) == 1
    assert results[0].error == "oops"


def test_fire_returns_event_per_callback(registry):
    registry.register("on_success", lambda j, c: None)
    registry.register("on_success", lambda j, c: None)
    job = _make_job()
    results = registry.fire("on_success", job)
    assert len(results) == 2
    assert all(r.event == "on_success" for r in results)


def test_fire_unknown_event_raises(registry):
    with pytest.raises(ValueError):
        registry.fire("on_timeout", _make_job())


# ---------------------------------------------------------------------------
# Clear
# ---------------------------------------------------------------------------

def test_clear_specific_event(registry):
    registry.register("on_start", lambda j, c: None)
    registry.register("on_success", lambda j, c: None)
    registry.clear("on_start")
    assert registry.count("on_start") == 0
    assert registry.count("on_success") == 1


def test_clear_all_events(registry):
    for ev in ("on_start", "on_success", "on_failure"):
        registry.register(ev, lambda j, c: None)
    registry.clear()
    for ev in ("on_start", "on_success", "on_failure"):
        assert registry.count(ev) == 0
