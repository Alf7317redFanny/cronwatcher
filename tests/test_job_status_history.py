"""Tests for StatusHistoryAnalyzer."""
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from cronwatcher.job_status_history import StatusHistoryAnalyzer, StatusTrend
from cronwatcher.history import RunRecord


def _rec(job: str, success: bool, ts: float = 0.0) -> RunRecord:
    r = MagicMock(spec=RunRecord)
    r.job_name = job
    r.success = success
    r.ran_at = datetime.fromtimestamp(ts, tz=timezone.utc)
    return r


@pytest.fixture
def history():
    h = MagicMock()
    h.records = [
        _rec("backup", True, 1),
        _rec("backup", True, 2),
        _rec("backup", False, 3),
        _rec("sync", False, 1),
        _rec("sync", False, 2),
    ]
    return h


@pytest.fixture
def analyzer(history):
    return StatusHistoryAnalyzer(history, window=10)


def test_analyze_counts_runs(analyzer):
    t = analyzer.analyze("backup")
    assert t.total_runs == 3


def test_analyze_counts_failures(analyzer):
    t = analyzer.analyze("backup")
    assert t.total_failures == 1


def test_success_rate(analyzer):
    t = analyzer.analyze("backup")
    assert t.success_rate == pytest.approx(66.7)


def test_last_status_fail(analyzer):
    t = analyzer.analyze("backup")
    assert t.last_status == "fail"


def test_last_status_unknown_for_missing_job(analyzer):
    t = analyzer.analyze("nonexistent")
    assert t.last_status is None
    assert t.total_runs == 0


def test_success_rate_zero_when_no_runs(analyzer):
    t = analyzer.analyze("ghost")
    assert t.success_rate == 0.0


def test_recent_window_respected():
    h = MagicMock()
    h.records = [_rec("job", i % 2 == 0, float(i)) for i in range(20)]
    a = StatusHistoryAnalyzer(h, window=5)
    t = a.analyze("job")
    assert len(t.recent) == 5


def test_analyze_all_returns_dict(analyzer):
    result = analyzer.analyze_all(["backup", "sync"])
    assert set(result.keys()) == {"backup", "sync"}
    assert isinstance(result["backup"], StatusTrend)


def test_repr_contains_job_name(analyzer):
    t = analyzer.analyze("backup")
    assert "backup" in repr(t)
    assert "StatusTrend" in repr(t)


def test_all_success_rate_100():
    h = MagicMock()
    h.records = [_rec("clean", True, float(i)) for i in range(5)]
    a = StatusHistoryAnalyzer(h)
    t = a.analyze("clean")
    assert t.success_rate == 100.0
