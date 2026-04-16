"""Tests for HookRegistry."""
import pytest
from cronwatcher.job_runner_hooks import HookRegistry


@pytest.fixture
def registry():
    return HookRegistry()


def test_repr(registry):
    assert "HookRegistry" in repr(registry)


def test_register_and_run_pre(registry):
    called = []
    registry.register_pre(lambda name: called.append(("pre", name)))
    registry.run_pre("backup")
    assert called == [("pre", "backup")]


def test_register_and_run_post(registry):
    called = []
    registry.register_post(lambda name: called.append(("post", name)))
    registry.run_post("backup")
    assert called == [("post", "backup")]


def test_register_and_run_failure(registry):
    called = []
    registry.register_failure(lambda name: called.append(("fail", name)))
    registry.run_failure("backup")
    assert called == [("fail", "backup")]


def test_multiple_hooks_all_called(registry):
    log = []
    registry.register_pre(lambda n: log.append(f"a:{n}"))
    registry.register_pre(lambda n: log.append(f"b:{n}"))
    registry.run_pre("sync")
    assert log == ["a:sync", "b:sync"]


def test_no_hooks_runs_cleanly(registry):
    registry.run_pre("noop")
    registry.run_post("noop")
    registry.run_failure("noop")


def test_clear_removes_all_hooks(registry):
    log = []
    registry.register_pre(lambda n: log.append(n))
    registry.clear()
    registry.run_pre("x")
    assert log == []


def test_hooks_receive_correct_job_name(registry):
    names = []
    registry.register_post(lambda n: names.append(n))
    registry.run_post("my-job")
    assert names == ["my-job"]


def test_failure_hook_not_called_on_success(registry):
    log = []
    registry.register_failure(lambda n: log.append(n))
    registry.run_post("ok-job")
    assert log == []
