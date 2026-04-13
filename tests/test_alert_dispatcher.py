"""Tests for cronwatcher.alert_dispatcher."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.alert_dispatcher import AlertDispatcher, DispatchResult
from cronwatcher.plugins import AlertPlugin
from cronwatcher.ratelimit import RateLimitConfig


def _make_config(tmp_path: Path, max_alerts: int = 5) -> RateLimitConfig:
    return RateLimitConfig(
        max_alerts=max_alerts,
        window_seconds=3600,
        state_file=str(tmp_path / "rl.json"),
    )


def _mock_plugin(name: str = "mock") -> AlertPlugin:
    plugin = MagicMock(spec=AlertPlugin)
    plugin.name = name
    return plugin


def test_dispatch_calls_all_plugins(tmp_path: Path) -> None:
    p1, p2 = _mock_plugin("p1"), _mock_plugin("p2")
    dispatcher = AlertDispatcher([p1, p2], _make_config(tmp_path))
    result = dispatcher.dispatch("myjob", "Subject", "Body")
    p1.send.assert_called_once_with("Subject", "Body")
    p2.send.assert_called_once_with("Subject", "Body")
    assert result.sent is True
    assert result.job_name == "myjob"


def test_dispatch_returns_result_with_no_errors(tmp_path: Path) -> None:
    dispatcher = AlertDispatcher([_mock_plugin()], _make_config(tmp_path))
    result = dispatcher.dispatch("job", "s", "b")
    assert result.plugin_errors == []
    assert result.skipped_reason is None


def test_plugin_exception_recorded_in_result(tmp_path: Path) -> None:
    plugin = _mock_plugin("bad")
    plugin.send.side_effect = RuntimeError("smtp down")
    dispatcher = AlertDispatcher([plugin], _make_config(tmp_path))
    result = dispatcher.dispatch("job", "s", "b")
    assert result.sent is True
    assert len(result.plugin_errors) == 1
    assert "bad" in result.plugin_errors[0]


def test_rate_limit_blocks_dispatch(tmp_path: Path) -> None:
    plugin = _mock_plugin()
    config = _make_config(tmp_path, max_alerts=2)
    dispatcher = AlertDispatcher([plugin], config)
    dispatcher.dispatch("job", "s", "b")
    dispatcher.dispatch("job", "s", "b")
    result = dispatcher.dispatch("job", "s", "b")
    assert result.sent is False
    assert result.skipped_reason == "rate_limit_exceeded"
    assert plugin.send.call_count == 2


def test_remaining_quota_decrements(tmp_path: Path) -> None:
    config = _make_config(tmp_path, max_alerts=3)
    dispatcher = AlertDispatcher([_mock_plugin()], config)
    assert dispatcher.remaining_quota("job") == 3
    dispatcher.dispatch("job", "s", "b")
    assert dispatcher.remaining_quota("job") == 2


def test_different_jobs_independent_quota(tmp_path: Path) -> None:
    config = _make_config(tmp_path, max_alerts=1)
    dispatcher = AlertDispatcher([_mock_plugin()], config)
    dispatcher.dispatch("jobA", "s", "b")
    result = dispatcher.dispatch("jobB", "s", "b")
    assert result.sent is True


def test_dispatch_repr(tmp_path: Path) -> None:
    dispatcher = AlertDispatcher([_mock_plugin()], _make_config(tmp_path))
    result = dispatcher.dispatch("job", "s", "b")
    assert "job" in repr(result)
    assert "sent=True" in repr(result)
