"""Tests for cronwatcher.job_baseline."""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from cronwatcher.job_baseline import BaselineIndex, BaselineRecord, DeviationResult


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "baselines.json"


@pytest.fixture
def index(state_file: Path) -> BaselineIndex:
    return BaselineIndex(state_file, z_threshold=2.0)


# --- BaselineRecord ---

def test_record_repr():
    rec = BaselineRecord("backup", 30.0, 5.0, 10)
    assert "backup" in repr(rec)
    assert "30.00s" in repr(rec)


def test_record_roundtrip():
    rec = BaselineRecord("sync", 12.5, 1.2, 8)
    assert BaselineRecord.from_dict(rec.to_dict()) == rec


# --- BaselineIndex basics ---

def test_starts_empty(index: BaselineIndex):
    assert index.all_baselines() == []


def test_load_nonexistent_is_noop(state_file: Path):
    idx = BaselineIndex(state_file)
    assert idx.get("anything") is None


def test_update_returns_record(index: BaselineIndex):
    rec = index.update("backup", [10.0, 12.0, 11.0, 13.0, 9.0])
    assert isinstance(rec, BaselineRecord)
    assert rec.job_name == "backup"
    assert rec.sample_count == 5


def test_update_computes_mean(index: BaselineIndex):
    rec = index.update("job", [10.0, 20.0])
    assert rec.mean_seconds == pytest.approx(15.0)


def test_update_requires_at_least_two_samples(index: BaselineIndex):
    result = index.update("job", [10.0])
    assert result is None
    assert index.get("job") is None


def test_update_persists_to_disk(index: BaselineIndex, state_file: Path):
    index.update("daily", [60.0, 62.0, 58.0])
    raw = json.loads(state_file.read_text())
    assert "daily" in raw


def test_get_returns_none_for_unknown(index: BaselineIndex):
    assert index.get("nonexistent") is None


def test_get_returns_stored_record(index: BaselineIndex):
    index.update("etl", [5.0, 6.0, 7.0])
    rec = index.get("etl")
    assert rec is not None
    assert rec.job_name == "etl"


def test_all_baselines_lists_all(index: BaselineIndex):
    index.update("a", [1.0, 2.0])
    index.update("b", [10.0, 20.0])
    names = {r.job_name for r in index.all_baselines()}
    assert names == {"a", "b"}


def test_index_reloads_from_disk(state_file: Path):
    idx1 = BaselineIndex(state_file)
    idx1.update("nightly", [100.0, 110.0, 90.0])
    idx2 = BaselineIndex(state_file)
    rec = idx2.get("nightly")
    assert rec is not None
    assert rec.sample_count == 3


# --- DeviationResult ---

def test_check_deviation_returns_none_without_baseline(index: BaselineIndex):
    result = index.check_deviation("unknown", 30.0)
    assert result is None


def test_check_deviation_ok_within_threshold(index: BaselineIndex):
    index.update("job", [10.0, 10.0, 10.0, 10.0, 10.0, 10.0])
    result = index.check_deviation("job", 10.5)
    assert isinstance(result, DeviationResult)
    assert not result.is_anomaly


def test_check_deviation_flags_anomaly(index: BaselineIndex):
    index.update("job", [10.0, 11.0, 9.0, 10.5, 9.5])
    result = index.check_deviation("job", 100.0)
    assert result.is_anomaly
    assert result.z_score > 2.0


def test_deviation_result_repr():
    rec = BaselineRecord("j", 10.0, 1.0, 5)
    dr = DeviationResult("j", 50.0, rec, 40.0, True)
    assert "ANOMALY" in repr(dr)
    assert "j" in repr(dr)
