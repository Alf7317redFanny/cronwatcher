"""Tests for cronwatcher.job_cooldown."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cronwatcher.job_cooldown import CooldownManager, CooldownPolicy, CooldownState


# ---------------------------------------------------------------------------
# CooldownPolicy
# ---------------------------------------------------------------------------

def test_policy_defaults():
    p = CooldownPolicy()
    assert p.default_seconds == 60


def test_policy_per_job_override():
    p = CooldownPolicy(default_seconds=30, per_job={"backup": 120})
    assert p.seconds_for("backup") == 120
    assert p.seconds_for("other") == 30


def test_policy_negative_default_raises():
    with pytest.raises(ValueError, match="default_seconds"):
        CooldownPolicy(default_seconds=-1)


def test_policy_negative_per_job_raises():
    with pytest.raises(ValueError, match="cooldown for 'x'"):
        CooldownPolicy(per_job={"x": -5})


# ---------------------------------------------------------------------------
# CooldownState serialisation
# ---------------------------------------------------------------------------

def test_cooldown_state_roundtrip():
    now = datetime(2024, 6, 1, 12, 0, 0)
    s = CooldownState(job_name="sync", last_run=now)
    assert CooldownState.from_dict(s.to_dict()) == s


# ---------------------------------------------------------------------------
# CooldownManager fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "cooldown.json"


@pytest.fixture()
def policy() -> CooldownPolicy:
    return CooldownPolicy(default_seconds=60, per_job={"fast": 10})


@pytest.fixture()
def manager(policy: CooldownPolicy, state_file: Path) -> CooldownManager:
    return CooldownManager(policy=policy, state_file=state_file)


# ---------------------------------------------------------------------------
# CooldownManager behaviour
# ---------------------------------------------------------------------------

def test_no_cooldown_before_first_run(manager: CooldownManager):
    assert manager.is_cooling_down("myjob") is False


def test_cooling_down_immediately_after_run(manager: CooldownManager):
    now = datetime.utcnow()
    manager.record_run("myjob", when=now)
    assert manager.is_cooling_down("myjob", now=now + timedelta(seconds=5)) is True


def test_not_cooling_down_after_gap_elapsed(manager: CooldownManager):
    past = datetime.utcnow() - timedelta(seconds=120)
    manager.record_run("myjob", when=past)
    assert manager.is_cooling_down("myjob") is False


def test_per_job_override_respected(manager: CooldownManager):
    now = datetime.utcnow()
    manager.record_run("fast", when=now)
    # 5 s < 10 s override → still cooling
    assert manager.is_cooling_down("fast", now=now + timedelta(seconds=5)) is True
    # 15 s > 10 s override → done
    assert manager.is_cooling_down("fast", now=now + timedelta(seconds=15)) is False


def test_remaining_seconds_decreases(manager: CooldownManager):
    now = datetime.utcnow()
    manager.record_run("myjob", when=now)
    r = manager.remaining_seconds("myjob", now=now + timedelta(seconds=10))
    assert 49 < r <= 50


def test_remaining_seconds_zero_when_expired(manager: CooldownManager):
    past = datetime.utcnow() - timedelta(seconds=200)
    manager.record_run("myjob", when=past)
    assert manager.remaining_seconds("myjob") == 0.0


def test_state_persisted_to_disk(policy: CooldownPolicy, state_file: Path):
    m = CooldownManager(policy=policy, state_file=state_file)
    m.record_run("persist_job")
    data = json.loads(state_file.read_text())
    assert any(e["job_name"] == "persist_job" for e in data)


def test_state_loaded_from_disk(policy: CooldownPolicy, state_file: Path):
    m1 = CooldownManager(policy=policy, state_file=state_file)
    now = datetime.utcnow()
    m1.record_run("reload_job", when=now)

    m2 = CooldownManager(policy=policy, state_file=state_file)
    assert m2.is_cooling_down("reload_job", now=now + timedelta(seconds=1)) is True
