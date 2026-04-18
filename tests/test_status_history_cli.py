"""Tests for status_history_cli."""
import argparse
import pytest
from unittest.mock import MagicMock
from cronwatcher.status_history_cli import add_status_history_args, run_trends_cmd, _bar
from cronwatcher.job_status_history import StatusTrend


@pytest.fixture
def parser():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers()
    add_status_history_args(sub)
    return p


@pytest.fixture
def analyzer():
    a = MagicMock()
    t1 = StatusTrend(job_name="backup", recent=["ok", "ok", "fail"], total_runs=10, total_failures=2)
    t2 = StatusTrend(job_name="sync", recent=["fail", "fail"], total_runs=5, total_failures=5)
    a.analyze_all.return_value = {"backup": t1, "sync": t2}
    return a


def test_add_status_history_args_registers_trends(parser):
    args = parser.parse_args(["trends"])
    assert args.cmd == "trends"


def test_add_status_history_args_window_default(parser):
    args = parser.parse_args(["trends"])
    assert args.window == 10


def test_add_status_history_args_window_custom(parser):
    args = parser.parse_args(["trends", "--window", "5"])
    assert args.window == 5


def test_add_status_history_args_job_filter(parser):
    args = parser.parse_args(["trends", "--job", "backup"])
    assert args.job == "backup"


def test_run_trends_cmd_returns_zero(analyzer, capsys):
    args = argparse.Namespace(job=None, window=10)
    rc = run_trends_cmd(args, analyzer, ["backup", "sync"])
    assert rc == 0


def test_run_trends_cmd_prints_header(analyzer, capsys):
    args = argparse.Namespace(job=None, window=10)
    run_trends_cmd(args, analyzer, ["backup", "sync"])
    out = capsys.readouterr().out
    assert "Job" in out
    assert "Rate" in out


def test_run_trends_cmd_filters_by_job(analyzer, capsys):
    t = StatusTrend(job_name="backup", recent=["ok"], total_runs=1, total_failures=0)
    analyzer.analyze_all.return_value = {"backup": t}
    args = argparse.Namespace(job="backup", window=10)
    run_trends_cmd(args, analyzer, ["backup", "sync"])
    analyzer.analyze_all.assert_called_once_with(["backup"])


def test_bar_all_ok():
    assert _bar(["ok", "ok", "ok"]) == "▓▓▓"


def test_bar_all_fail():
    assert _bar(["fail", "fail"]) == "░░"


def test_bar_respects_width():
    recent = ["ok"] * 20
    assert len(_bar(recent, width=5)) == 5


def test_run_trends_no_jobs(capsys):
    a = MagicMock()
    a.analyze_all.return_value = {}
    args = argparse.Namespace(job=None, window=10)
    rc = run_trends_cmd(args, a, [])
    assert rc == 0
    assert "No jobs" in capsys.readouterr().out
