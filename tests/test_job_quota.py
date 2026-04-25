"""Tests for cronwatcher/job_quota.py"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwatcher.job_quota import QuotaManager, QuotaPolicy, QuotaState


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "quota.json"


@pytest.fixture
def policy() -> QuotaPolicy:
    return QuotaPolicy(max_runs=3, window_seconds=60)


@pytest.fixture
def manager(policy: QuotaPolicy, state_file: Path) -> QuotaManager:
    return QuotaManager(policy=policy, state_file=state_file)


def test_policy_defaults() -> None:
    p = QuotaPolicy()
    assert p.max_runs == 0
    assert p.window_seconds == 3600


def test_policy_invalid_max_raises() -> None:
    with pytest.raises(ValueError, match="max_runs"):
        QuotaPolicy(max_runs=-1)


def test_policy_invalid_window_raises() -> None:
    with pytest.raises(ValueError, match="window_seconds"):
        QuotaPolicy(window_seconds=0)


def test_policy_invalid_per_job_raises() -> None:
    with pytest.raises(ValueError, match="per_job"):
        QuotaPolicy(per_job={"myjob": -2})


def test_limit_for_uses_per_job_override() -> None:
    p = QuotaPolicy(max_runs=5, per_job={"special": 10})
    assert p.limit_for("special") == 10
    assert p.limit_for("other") == 5


def test_unlimited_when_max_runs_zero(manager: QuotaManager, state_file: Path) -> None:
    p = QuotaPolicy(max_runs=0)
    m = QuotaManager(policy=p, state_file=state_file)
    for _ in range(100):
        assert m.allowed("anyjob") is True


def test_allowed_before_limit(manager: QuotaManager) -> None:
    assert manager.allowed("jobA") is True


def test_not_allowed_after_limit_reached(manager: QuotaManager) -> None:
    for _ in range(3):
        manager.record("jobA")
    assert manager.allowed("jobA") is False


def test_usage_increments_on_record(manager: QuotaManager) -> None:
    manager.record("jobB")
    manager.record("jobB")
    assert manager.usage("jobB") == 2


def test_usage_zero_for_unknown_job(manager: QuotaManager) -> None:
    assert manager.usage("unknown") == 0


def test_state_persists_to_disk(manager: QuotaManager, state_file: Path, policy: QuotaPolicy) -> None:
    manager.record("jobC")
    m2 = QuotaManager(policy=policy, state_file=state_file)
    assert m2.usage("jobC") == 1


def test_old_timestamps_pruned(state_file: Path) -> None:
    p = QuotaPolicy(max_runs=2, window_seconds=1)
    m = QuotaManager(policy=p, state_file=state_file)
    m.record("jobD")
    m.record("jobD")
    assert m.allowed("jobD") is False
    # Manually backdate timestamps
    state = m._states["jobD"]
    state.timestamps = [t - 10 for t in state.timestamps]
    m._save()
    # Reload
    m2 = QuotaManager(policy=p, state_file=state_file)
    assert m2.allowed("jobD") is True


def test_quota_state_roundtrip() -> None:
    s = QuotaState(job_name="x", timestamps=[1.0, 2.0])
    d = s.to_dict()
    s2 = QuotaState.from_dict(d)
    assert s2.job_name == "x"
    assert s2.timestamps == [1.0, 2.0]
