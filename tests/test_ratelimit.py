"""Tests for cronwatcher.ratelimit."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwatcher.ratelimit import RateLimitConfig, RateLimiter, RateLimitState


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "rl_state.json"


@pytest.fixture
def config(state_file: Path) -> RateLimitConfig:
    return RateLimitConfig(max_alerts=3, window_seconds=60, state_file=str(state_file))


@pytest.fixture
def limiter(config: RateLimitConfig) -> RateLimiter:
    return RateLimiter(config)


def test_config_invalid_max_alerts_raises() -> None:
    with pytest.raises(ValueError, match="max_alerts"):
        RateLimitConfig(max_alerts=0)


def test_config_invalid_window_raises() -> None:
    with pytest.raises(ValueError, match="window_seconds"):
        RateLimitConfig(window_seconds=0)


def test_is_allowed_initially(limiter: RateLimiter) -> None:
    assert limiter.is_allowed("backup") is True


def test_remaining_full_quota(limiter: RateLimiter) -> None:
    assert limiter.remaining("backup") == 3


def test_record_decrements_remaining(limiter: RateLimiter) -> None:
    limiter.record("backup")
    assert limiter.remaining("backup") == 2


def test_blocked_after_max_alerts(limiter: RateLimiter) -> None:
    for _ in range(3):
        limiter.record("backup")
    assert limiter.is_allowed("backup") is False
    assert limiter.remaining("backup") == 0


def test_different_jobs_are_independent(limiter: RateLimiter) -> None:
    for _ in range(3):
        limiter.record("jobA")
    assert limiter.is_allowed("jobA") is False
    assert limiter.is_allowed("jobB") is True


def test_state_persisted_to_disk(limiter: RateLimiter, state_file: Path) -> None:
    limiter.record("backup")
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert "backup" in data["timestamps"]
    assert len(data["timestamps"]["backup"]) == 1


def test_state_loaded_from_disk(config: RateLimitConfig, state_file: Path) -> None:
    l1 = RateLimiter(config)
    l1.record("backup")
    l1.record("backup")
    l2 = RateLimiter(config)
    assert l2.remaining("backup") == 1


def test_old_timestamps_pruned(config: RateLimitConfig, state_file: Path) -> None:
    old = time.time() - 120
    state_file.write_text(json.dumps({"timestamps": {"backup": [old, old]}}))
    limiter = RateLimiter(config)
    assert limiter.is_allowed("backup") is True
    assert limiter.remaining("backup") == 3


def test_corrupt_state_file_handled(config: RateLimitConfig, state_file: Path) -> None:
    state_file.write_text("not-json{{")
    limiter = RateLimiter(config)
    assert limiter.is_allowed("job") is True
