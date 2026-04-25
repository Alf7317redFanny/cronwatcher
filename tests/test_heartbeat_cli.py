"""Tests for cronwatcher/heartbeat_cli.py"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from cronwatcher.heartbeat_cli import add_heartbeat_args, heartbeat_summary, run_heartbeat_cmd
from cronwatcher.job_heartbeat import HeartbeatIndex


@pytest.fixture
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command")
    add_heartbeat_args(sub)
    return p


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "hb.json"


def _args(parser: argparse.ArgumentParser, *argv: str) -> argparse.Namespace:
    return parser.parse_args(argv)


def test_add_heartbeat_args_registers_subcommand(parser: argparse.ArgumentParser) -> None:
    ns = _args(parser, "heartbeat", "ping", "myjob", "--state-file", "/tmp/hb.json")
    assert ns.command == "heartbeat"


def test_ping_action_returns_zero(parser: argparse.ArgumentParser, state_file: Path) -> None:
    ns = _args(parser, "heartbeat", "ping", "backup", "--state-file", str(state_file))
    assert run_heartbeat_cmd(ns) == 0


def test_ping_creates_record(parser: argparse.ArgumentParser, state_file: Path) -> None:
    ns = _args(parser, "heartbeat", "ping", "backup", "--state-file", str(state_file))
    run_heartbeat_cmd(ns)
    idx = HeartbeatIndex(state_file)
    assert idx.get("backup") is not None


def test_ping_with_interval(parser: argparse.ArgumentParser, state_file: Path) -> None:
    ns = _args(parser, "heartbeat", "ping", "backup", "--interval", "120", "--state-file", str(state_file))
    run_heartbeat_cmd(ns)
    idx = HeartbeatIndex(state_file)
    assert idx.get("backup").interval_seconds == 120


def test_status_empty_returns_zero(parser: argparse.ArgumentParser, state_file: Path) -> None:
    ns = _args(parser, "heartbeat", "status", "--state-file", str(state_file))
    assert run_heartbeat_cmd(ns) == 0


def test_status_stale_only_flag(parser: argparse.ArgumentParser, state_file: Path) -> None:
    ns = _args(parser, "heartbeat", "status", "--stale-only", "--state-file", str(state_file))
    assert ns.stale_only is True
    assert run_heartbeat_cmd(ns) == 0


def test_heartbeat_summary_format(state_file: Path) -> None:
    idx = HeartbeatIndex(state_file, default_interval=60)
    idx.ping("a")
    idx.ping("b")
    summary = heartbeat_summary(idx)
    assert "2 tracked" in summary
