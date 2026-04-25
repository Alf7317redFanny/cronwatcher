"""Tests for cronwatcher/quota_cli.py"""
from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from cronwatcher.quota_cli import add_quota_args, quota_summary, run_quota_cmd
from cronwatcher.job_quota import QuotaManager, QuotaPolicy


@pytest.fixture
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command")
    add_quota_args(sub)
    return p


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "quota_state.json"


def _args(parser: argparse.ArgumentParser, argv: list) -> argparse.Namespace:
    return parser.parse_args(argv)


def test_add_quota_args_registers_subcommand(parser: argparse.ArgumentParser) -> None:
    ns = _args(parser, ["quota", "status", "myjob"])
    assert ns.command == "quota"
    assert ns.quota_action == "status"
    assert ns.job == "myjob"


def test_status_defaults(parser: argparse.ArgumentParser) -> None:
    ns = _args(parser, ["quota", "status", "myjob"])
    assert ns.max_runs == 0
    assert ns.window_seconds == 3600


def test_status_action_returns_zero(parser: argparse.ArgumentParser, state_file: Path, capsys) -> None:
    ns = _args(parser, ["quota", "status", "myjob", "--state-file", str(state_file), "--max-runs", "5"])
    rc = run_quota_cmd(ns)
    assert rc == 0
    out = capsys.readouterr().out
    assert "myjob" in out
    assert "0 / 5" in out


def test_status_shows_unlimited_when_zero(parser: argparse.ArgumentParser, state_file: Path, capsys) -> None:
    ns = _args(parser, ["quota", "status", "anyjob", "--state-file", str(state_file)])
    run_quota_cmd(ns)
    out = capsys.readouterr().out
    assert "unlimited" in out


def test_reset_action_returns_zero(parser: argparse.ArgumentParser, state_file: Path, capsys) -> None:
    ns = _args(parser, ["quota", "reset", "myjob", "--state-file", str(state_file)])
    rc = run_quota_cmd(ns)
    assert rc == 0
    out = capsys.readouterr().out
    assert "reset" in out


def test_reset_clears_usage(state_file: Path, parser: argparse.ArgumentParser) -> None:
    policy = QuotaPolicy(max_runs=3, window_seconds=60)
    manager = QuotaManager(policy=policy, state_file=state_file)
    manager.record("jobX")
    manager.record("jobX")
    assert manager.usage("jobX") == 2

    ns = _args(parser, ["quota", "reset", "jobX", "--state-file", str(state_file)])
    run_quota_cmd(ns)

    manager2 = QuotaManager(policy=policy, state_file=state_file)
    assert manager2.usage("jobX") == 0


def test_quota_summary_output(state_file: Path) -> None:
    policy = QuotaPolicy(max_runs=5, window_seconds=60)
    manager = QuotaManager(policy=policy, state_file=state_file)
    manager.record("alpha")
    manager.record("alpha")
    result = quota_summary(manager, ["alpha", "beta"])
    assert "alpha: 2/5" in result
    assert "beta: 0/5" in result


def test_quota_summary_unlimited(state_file: Path) -> None:
    policy = QuotaPolicy(max_runs=0)
    manager = QuotaManager(policy=policy, state_file=state_file)
    result = quota_summary(manager, ["gamma"])
    assert "gamma: 0/∞" in result
