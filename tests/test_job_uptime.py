"""Tests for cronwatcher.job_uptime."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta

import pytest

from cronwatcher.history import History, RunRecord
from cronwatcher.job_uptime import UptimeAnalyzer, UptimeResult


@pytest.fixture()
def tmp_history_path(tmp_path):
    return str(tmp_path / "history.json")


def _rec(job_name: str, success: bool, offset_hours: int = 0) -> RunRecord:
    started = datetime.utcnow() - timedelta(hours=offset_hours)
    return RunRecord(
        job_name=job_name,
        started_at=started,
        duration=1.0,
        success=success,
        exit_code=0 if success else 1,
        output="",
    )


@pytest.fixture()
def history(tmp_history_path):
    h = History(tmp_history_path)
    h.add(_rec("backup", True, offset_hours=2))
    h.add(_rec("backup", True, offset_hours=4))
    h.add(_rec("backup", False, offset_hours=6))
    h.add(_rec("sync", True, offset_hours=1))
    h.add(_rec("sync", False, offset_hours=3))
    return h


@pytest.fixture()
def analyzer(history):
    return UptimeAnalyzer(history, window_days=30)


def test_analyze_counts_total_runs(analyzer):
    result = analyzer.analyze("backup")
    assert result.total_runs == 3


def test_analyze_counts_successful_runs(analyzer):
    result = analyzer.analyze("backup")
    assert result.successful_runs == 2


def test_analyze_uptime_pct(analyzer):
    result = analyzer.analyze("backup")
    assert abs(result.uptime_pct - 66.6667) < 0.01


def test_analyze_no_runs_returns_zero_pct(analyzer):
    result = analyzer.analyze("nonexistent")
    assert result.total_runs == 0
    assert result.uptime_pct == 0.0


def test_analyze_all_returns_one_per_job(analyzer):
    results = analyzer.analyze_all(["backup", "sync"])
    assert len(results) == 2
    names = {r.job_name for r in results}
    assert names == {"backup", "sync"}


def test_window_days_filters_old_records(tmp_history_path):
    h = History(tmp_history_path)
    h.add(_rec("job", True, offset_hours=2))
    h.add(_rec("job", False, offset_hours=24 * 40))  # 40 days ago — outside window
    a = UptimeAnalyzer(h, window_days=30)
    result = a.analyze("job")
    assert result.total_runs == 1
    assert result.successful_runs == 1


def test_result_to_dict_keys(analyzer):
    result = analyzer.analyze("backup")
    d = result.to_dict()
    assert set(d.keys()) == {"job_name", "total_runs", "successful_runs", "uptime_pct", "window_days", "since"}


def test_result_repr(analyzer):
    result = analyzer.analyze("backup")
    assert "backup" in repr(result)
    assert "uptime=" in repr(result)


def test_invalid_window_raises():
    with pytest.raises(ValueError, match="window_days"):
        UptimeAnalyzer(None, window_days=0)  # type: ignore
