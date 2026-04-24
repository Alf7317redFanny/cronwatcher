"""Tests for cronwatcher/job_cost.py"""
import json
import pytest
from pathlib import Path
from cronwatcher.job_cost import CostRate, CostSample, CostTracker


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "cost_state.json"


@pytest.fixture
def rate() -> CostRate:
    return CostRate(default_rate=0.01, per_job={"backup": 0.05})


@pytest.fixture
def tracker(rate: CostRate, state_file: Path) -> CostTracker:
    return CostTracker(rate=rate, state_file=state_file)


# ── CostRate ──────────────────────────────────────────────────────────────────

def test_cost_rate_defaults():
    r = CostRate()
    assert r.default_rate == 0.0
    assert r.per_job == {}


def test_cost_rate_invalid_default_raises():
    with pytest.raises(ValueError, match="default_rate"):
        CostRate(default_rate=-1.0)


def test_cost_rate_invalid_per_job_raises():
    with pytest.raises(ValueError, match="backup"):
        CostRate(default_rate=0.01, per_job={"backup": -0.5})


def test_rate_for_uses_per_job_override(rate: CostRate):
    assert rate.rate_for("backup") == 0.05


def test_rate_for_falls_back_to_default(rate: CostRate):
    assert rate.rate_for("cleanup") == 0.01


# ── CostSample ────────────────────────────────────────────────────────────────

def test_cost_sample_roundtrip():
    s = CostSample(job_name="backup", duration_seconds=30.0, cost=1.5, timestamp="2024-01-01T00:00:00")
    assert CostSample.from_dict(s.to_dict()) == s


def test_cost_sample_repr():
    s = CostSample(job_name="backup", duration_seconds=10.0, cost=0.5, timestamp="2024-01-01T00:00:00")
    assert "backup" in repr(s)
    assert "0.5000" in repr(s)


# ── CostTracker ───────────────────────────────────────────────────────────────

def test_tracker_starts_empty(tracker: CostTracker):
    assert tracker.all_samples() == []


def test_record_returns_sample(tracker: CostTracker):
    sample = tracker.record("backup", 20.0, "2024-01-01T00:00:00")
    assert isinstance(sample, CostSample)
    assert sample.job_name == "backup"
    assert sample.duration_seconds == 20.0
    assert sample.cost == pytest.approx(1.0)  # 0.05 * 20


def test_record_uses_default_rate(tracker: CostTracker):
    sample = tracker.record("cleanup", 100.0, "2024-01-01T00:00:00")
    assert sample.cost == pytest.approx(1.0)  # 0.01 * 100


def test_record_persists_to_disk(tracker: CostTracker, state_file: Path):
    tracker.record("backup", 10.0, "2024-01-01T00:00:00")
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert len(data) == 1
    assert data[0]["job_name"] == "backup"


def test_load_restores_samples(rate: CostRate, state_file: Path):
    t1 = CostTracker(rate=rate, state_file=state_file)
    t1.record("backup", 10.0, "2024-01-01T00:00:00")
    t2 = CostTracker(rate=rate, state_file=state_file)
    assert len(t2.all_samples()) == 1


def test_total_cost_all_jobs(tracker: CostTracker):
    tracker.record("backup", 10.0, "t1")
    tracker.record("cleanup", 50.0, "t2")
    assert tracker.total_cost() == pytest.approx(0.05 * 10 + 0.01 * 50)


def test_total_cost_filtered_by_job(tracker: CostTracker):
    tracker.record("backup", 10.0, "t1")
    tracker.record("cleanup", 50.0, "t2")
    assert tracker.total_cost("backup") == pytest.approx(0.5)


def test_samples_for_filters_correctly(tracker: CostTracker):
    tracker.record("backup", 10.0, "t1")
    tracker.record("cleanup", 5.0, "t2")
    tracker.record("backup", 20.0, "t3")
    result = tracker.samples_for("backup")
    assert len(result) == 2
    assert all(s.job_name == "backup" for s in result)
