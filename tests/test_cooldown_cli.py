"""Tests for cronwatcher.cooldown_cli."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cronwatcher.cooldown_cli import add_cooldown_args, run_cooldown_cmd
from cronwatcher.job_cooldown import CooldownManager, CooldownPolicy


@pytest.fixture()
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command")
    add_cooldown_args(sub)
    return p


@pytest.fixture()
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "cooldown.json"


def _args(parser: argparse.ArgumentParser, state_file: Path, *extra: str) -> argparse.Namespace:
    return parser.parse_args(["cooldown", *extra, "--state-file", str(state_file)])


def test_add_cooldown_args_registers_subcommand(parser: argparse.ArgumentParser):
    ns = parser.parse_args(["cooldown", "status", "myjob"])
    assert ns.command == "cooldown"
    assert ns.cooldown_action == "status"
    assert ns.job == "myjob"


def test_status_ready_job(parser: argparse.ArgumentParser, state_file: Path, capsys):
    ns = _args(parser, state_file, "status", "myjob")
    rc = run_cooldown_cmd(ns)
    assert rc == 0
    out = capsys.readouterr().out
    assert "ready" in out


def test_status_cooling_job(parser: argparse.ArgumentParser, state_file: Path, capsys):
    # Pre-populate state so the job is cooling.
    policy = CooldownPolicy(default_seconds=60)
    mgr = CooldownManager(policy=policy, state_file=state_file)
    mgr.record_run("hotjob", when=datetime.utcnow())

    ns = _args(parser, state_file, "status", "hotjob")
    rc = run_cooldown_cmd(ns)
    assert rc == 0
    out = capsys.readouterr().out
    assert "cooling down" in out


def test_reset_clears_cooldown(parser: argparse.ArgumentParser, state_file: Path, capsys):
    policy = CooldownPolicy(default_seconds=60)
    mgr = CooldownManager(policy=policy, state_file=state_file)
    mgr.record_run("hotjob", when=datetime.utcnow())

    ns = _args(parser, state_file, "reset", "hotjob")
    rc = run_cooldown_cmd(ns)
    assert rc == 0
    out = capsys.readouterr().out
    assert "reset" in out

    # Re-load manager and confirm no longer cooling.
    mgr2 = CooldownManager(policy=policy, state_file=state_file)
    assert mgr2.is_cooling_down("hotjob") is False


def test_default_seconds_flag(parser: argparse.ArgumentParser, state_file: Path):
    ns = parser.parse_args(
        ["cooldown", "status", "myjob", "--default-seconds", "120",
         "--state-file", str(state_file)]
    )
    assert ns.default_seconds == 120
