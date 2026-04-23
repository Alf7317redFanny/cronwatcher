"""Tests for cronwatcher.job_concurrency."""
from __future__ import annotations

import pytest
from pathlib import Path

from cronwatcher.job_concurrency import (
    ConcurrencyLimitError,
    ConcurrencyManager,
    ConcurrencyPolicy,
    ConcurrencySlot,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "concurrency.json"


@pytest.fixture()
def policy() -> ConcurrencyPolicy:
    return ConcurrencyPolicy(max_instances=2, per_job_overrides={"single": 1})


@pytest.fixture()
def manager(policy: ConcurrencyPolicy, state_file: Path) -> ConcurrencyManager:
    return ConcurrencyManager(policy, state_file)


# ---------------------------------------------------------------------------
# ConcurrencyPolicy
# ---------------------------------------------------------------------------

def test_policy_defaults() -> None:
    p = ConcurrencyPolicy()
    assert p.max_instances == 1


def test_policy_invalid_max_raises() -> None:
    with pytest.raises(ValueError, match="max_instances must be >= 1"):
        ConcurrencyPolicy(max_instances=0)


def test_policy_invalid_per_job_raises() -> None:
    with pytest.raises(ValueError, match="max_instances for 'bad'"):
        ConcurrencyPolicy(per_job_overrides={"bad": 0})


def test_policy_limit_for_uses_override(policy: ConcurrencyPolicy) -> None:
    assert policy.limit_for("single") == 1
    assert policy.limit_for("other") == 2


# ---------------------------------------------------------------------------
# ConcurrencySlot
# ---------------------------------------------------------------------------

def test_slot_roundtrip() -> None:
    slot = ConcurrencySlot(job_name="backup", pid=1234, started_at="2024-01-01T00:00:00")
    assert ConcurrencySlot.from_dict(slot.to_dict()) == slot


def test_slot_repr() -> None:
    slot = ConcurrencySlot(job_name="backup", pid=1234, started_at="2024-01-01T00:00:00")
    assert "backup" in repr(slot)
    assert "1234" in repr(slot)


# ---------------------------------------------------------------------------
# ConcurrencyManager
# ---------------------------------------------------------------------------

def test_starts_empty(manager: ConcurrencyManager) -> None:
    assert manager.active_for("backup") == []


def test_acquire_returns_slot(manager: ConcurrencyManager) -> None:
    slot = manager.acquire("backup", pid=42)
    assert slot.job_name == "backup"
    assert slot.pid == 42


def test_active_after_acquire(manager: ConcurrencyManager) -> None:
    manager.acquire("backup", pid=10)
    assert len(manager.active_for("backup")) == 1


def test_acquire_within_limit(manager: ConcurrencyManager) -> None:
    manager.acquire("backup", pid=10)
    manager.acquire("backup", pid=11)  # limit is 2
    assert len(manager.active_for("backup")) == 2


def test_acquire_exceeds_limit_raises(manager: ConcurrencyManager) -> None:
    manager.acquire("single", pid=10)  # limit is 1
    with pytest.raises(ConcurrencyLimitError):
        manager.acquire("single", pid=11)


def test_release_removes_slot(manager: ConcurrencyManager) -> None:
    slot = manager.acquire("backup", pid=10)
    manager.release(slot)
    assert manager.active_for("backup") == []


def test_release_all_returns_count(manager: ConcurrencyManager) -> None:
    manager.acquire("backup", pid=10)
    manager.acquire("backup", pid=11)
    count = manager.release_all("backup")
    assert count == 2
    assert manager.active_for("backup") == []


def test_state_persists_across_instances(policy: ConcurrencyPolicy, state_file: Path) -> None:
    m1 = ConcurrencyManager(policy, state_file)
    m1.acquire("backup", pid=99)
    m2 = ConcurrencyManager(policy, state_file)
    assert len(m2.active_for("backup")) == 1
