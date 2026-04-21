"""Tests for cronwatcher.job_metrics."""
import time
from pathlib import Path

import pytest

from cronwatcher.job_metrics import MetricSample, MetricsStore, JobMetricsSummary


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "metrics.json"


@pytest.fixture
def store(store_path: Path) -> MetricsStore:
    return MetricsStore(store_path)


def _sample(job: str = "backup", dur: float = 1.5, success: bool = True) -> MetricSample:
    return MetricSample(job_name=job, duration_seconds=dur, success=success)


def test_store_starts_empty(store: MetricsStore) -> None:
    assert store.all_job_names() == []


def test_record_returns_sample(store: MetricsStore) -> None:
    s = store.record(_sample())
    assert isinstance(s, MetricSample)
    assert s.job_name == "backup"


def test_samples_for_filters_by_job(store: MetricsStore) -> None:
    store.record(_sample("backup", 1.0))
    store.record(_sample("cleanup", 2.0))
    store.record(_sample("backup", 3.0))
    assert len(store.samples_for("backup")) == 2
    assert len(store.samples_for("cleanup")) == 1


def test_summarize_returns_none_for_unknown(store: MetricsStore) -> None:
    assert store.summarize("ghost") is None


def test_summarize_counts(store: MetricsStore) -> None:
    store.record(_sample("job", 2.0, True))
    store.record(_sample("job", 4.0, False))
    store.record(_sample("job", 6.0, True))
    s = store.summarize("job")
    assert s is not None
    assert s.total_runs == 3
    assert s.successful_runs == 2
    assert s.failed_runs == 1


def test_summarize_durations(store: MetricsStore) -> None:
    store.record(_sample("job", 1.0))
    store.record(_sample("job", 3.0))
    store.record(_sample("job", 5.0))
    s = store.summarize("job")
    assert s.min_duration == pytest.approx(1.0)
    assert s.max_duration == pytest.approx(5.0)
    assert s.avg_duration == pytest.approx(3.0)


def test_all_job_names_sorted(store: MetricsStore) -> None:
    store.record(_sample("zzz"))
    store.record(_sample("aaa"))
    store.record(_sample("mmm"))
    assert store.all_job_names() == ["aaa", "mmm", "zzz"]


def test_persistence_roundtrip(store_path: Path) -> None:
    s1 = MetricsStore(store_path)
    s1.record(_sample("backup", 2.5, True))
    s2 = MetricsStore(store_path)
    assert len(s2.samples_for("backup")) == 1
    assert s2.samples_for("backup")[0].duration_seconds == pytest.approx(2.5)


def test_sample_repr() -> None:
    s = _sample("myjob", 1.23, False)
    r = repr(s)
    assert "myjob" in r
    assert "fail" in r


def test_sample_to_dict_from_dict_roundtrip() -> None:
    s = _sample("myjob", 4.56, True)
    d = s.to_dict()
    s2 = MetricSample.from_dict(d)
    assert s2.job_name == s.job_name
    assert s2.duration_seconds == pytest.approx(s.duration_seconds)
    assert s2.success == s.success
