"""Tests for cronwatcher.uptime_cli."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatcher.job_uptime import UptimeAnalyzer, UptimeResult
from cronwatcher.uptime_cli import add_uptime_args, run_uptime_cmd, uptime_summary


@pytest.fixture()
def parser():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command")
    add_uptime_args(sub)
    return p


def _result(name: str, total: int, ok: int) -> UptimeResult:
    pct = (ok / total * 100.0) if total else 0.0
    return UptimeResult(
        job_name=name,
        total_runs=total,
        successful_runs=ok,
        uptime_pct=pct,
        window_days=30,
        since=datetime.utcnow() - timedelta(days=30),
    )


@pytest.fixture()
def analyzer():
    mock = MagicMock(spec=UptimeAnalyzer)
    mock.analyze_all.return_value = [
        _result("backup", 10, 9),
        _result("sync", 5, 5),
    ]
    return mock


def _args(parser, cmd_str: str) -> argparse.Namespace:
    return parser.parse_args(cmd_str.split())


def test_add_uptime_args_registers_subcommand(parser):
    ns = _args(parser, "uptime")
    assert ns.command == "uptime"


def test_window_default(parser):
    ns = _args(parser, "uptime")
    assert ns.window == 30


def test_window_custom(parser):
    ns = _args(parser, "uptime --window 7")
    assert ns.window == 7


def test_min_uptime_default(parser):
    ns = _args(parser, "uptime")
    assert ns.min_uptime == 0.0


def test_run_uptime_cmd_returns_zero(parser, analyzer, capsys):
    ns = _args(parser, "uptime")
    rc = run_uptime_cmd(ns, analyzer, ["backup", "sync"])
    assert rc == 0


def test_run_uptime_cmd_prints_jobs(parser, analyzer, capsys):
    ns = _args(parser, "uptime")
    run_uptime_cmd(ns, analyzer, ["backup", "sync"])
    out = capsys.readouterr().out
    assert "backup" in out
    assert "sync" in out


def test_min_uptime_filter_excludes_high_uptime(parser, capsys):
    mock = MagicMock(spec=UptimeAnalyzer)
    mock.analyze_all.return_value = [
        _result("backup", 10, 9),   # 90 %
        _result("flaky", 10, 5),    # 50 %
    ]
    ns = argparse.Namespace(window=30, job_names=[], min_uptime=80.0)
    run_uptime_cmd(ns, mock, ["backup", "flaky"])
    out = capsys.readouterr().out
    assert "flaky" in out
    assert "backup" not in out


def test_uptime_summary_format():
    results = [_result("backup", 10, 9), _result("sync", 4, 4)]
    text = uptime_summary(results)
    assert "backup" in text
    assert "90.0%" in text
    assert "sync" in text


def test_uptime_summary_empty():
    assert uptime_summary([]) == "No uptime data."
