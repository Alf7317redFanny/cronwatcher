"""Tests for cronwatcher.metrics_cli."""
import argparse
from pathlib import Path

import pytest

from cronwatcher.job_metrics import MetricSample, MetricsStore
from cronwatcher.metrics_cli import add_metrics_args, run_metrics_cmd


@pytest.fixture
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers()
    add_metrics_args(sub)
    return p


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "metrics.json"


def _args(parser: argparse.ArgumentParser, state_file: Path, extra: list = None) -> argparse.Namespace:
    argv = ["metrics", "--state-file", str(state_file)] + (extra or [])
    return parser.parse_args(argv)


def test_add_metrics_args_registers_subcommand(parser: argparse.ArgumentParser) -> None:
    ns = parser.parse_args(["metrics"])
    assert hasattr(ns, "func")


def test_empty_store_returns_zero(parser: argparse.ArgumentParser, state_file: Path) -> None:
    ns = _args(parser, state_file)
    assert run_metrics_cmd(ns) == 0


def test_metrics_cmd_with_data(parser: argparse.ArgumentParser, state_file: Path, capsys) -> None:
    store = MetricsStore(state_file)
    store.record(MetricSample("backup", 2.0, True))
    store.record(MetricSample("backup", 4.0, False))
    ns = _args(parser, state_file)
    rc = run_metrics_cmd(ns)
    assert rc == 0
    out = capsys.readouterr().out
    assert "backup" in out
    assert "2" in out  # total runs


def test_metrics_cmd_filter_by_job(parser: argparse.ArgumentParser, state_file: Path, capsys) -> None:
    store = MetricsStore(state_file)
    store.record(MetricSample("backup", 1.0, True))
    store.record(MetricSample("cleanup", 3.0, True))
    ns = _args(parser, state_file, ["--job", "backup"])
    run_metrics_cmd(ns)
    out = capsys.readouterr().out
    assert "backup" in out
    assert "cleanup" not in out


def test_metrics_cmd_unknown_job_shows_nothing(parser: argparse.ArgumentParser, state_file: Path, capsys) -> None:
    store = MetricsStore(state_file)
    store.record(MetricSample("backup", 1.0, True))
    ns = _args(parser, state_file, ["--job", "ghost"])
    rc = run_metrics_cmd(ns)
    assert rc == 0
    out = capsys.readouterr().out
    assert "ghost" not in out
