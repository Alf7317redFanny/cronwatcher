"""Tests for cronwatcher.runbook_cli."""
import argparse
import pytest
from pathlib import Path
from cronwatcher.runbook_cli import add_runbook_args, run_runbook_cmd
from cronwatcher.job_runbook import RunbookIndex


@pytest.fixture
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command")
    add_runbook_args(sub)
    return p


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "runbooks.json"


def _args(parser: argparse.ArgumentParser, cmdline: str) -> argparse.Namespace:
    return parser.parse_args(cmdline.split())


def test_add_runbook_args_registers_subcommand(parser: argparse.ArgumentParser) -> None:
    ns = _args(parser, "runbook list")
    assert ns.command == "runbook"


def test_set_action_returns_zero(parser: argparse.ArgumentParser, state_file: Path) -> None:
    ns = parser.parse_args(["runbook", "set", "myjob", "--url", "https://wiki", "--state-file", str(state_file)])
    assert run_runbook_cmd(ns) == 0


def test_set_persists_entry(parser: argparse.ArgumentParser, state_file: Path) -> None:
    ns = parser.parse_args(["runbook", "set", "myjob", "--step", "do this", "--state-file", str(state_file)])
    run_runbook_cmd(ns)
    idx = RunbookIndex(state_file)
    e = idx.get("myjob")
    assert e is not None
    assert e.steps == ["do this"]


def test_get_missing_returns_nonzero(parser: argparse.ArgumentParser, state_file: Path) -> None:
    ns = parser.parse_args(["runbook", "get", "ghost", "--state-file", str(state_file)])
    assert run_runbook_cmd(ns) == 1


def test_get_existing_returns_zero(parser: argparse.ArgumentParser, state_file: Path) -> None:
    idx = RunbookIndex(state_file)
    idx.set("known", url="https://x")
    ns = parser.parse_args(["runbook", "get", "known", "--state-file", str(state_file)])
    assert run_runbook_cmd(ns) == 0


def test_remove_existing_returns_zero(parser: argparse.ArgumentParser, state_file: Path) -> None:
    idx = RunbookIndex(state_file)
    idx.set("todel")
    ns = parser.parse_args(["runbook", "remove", "todel", "--state-file", str(state_file)])
    assert run_runbook_cmd(ns) == 0


def test_remove_missing_returns_nonzero(parser: argparse.ArgumentParser, state_file: Path) -> None:
    ns = parser.parse_args(["runbook", "remove", "ghost", "--state-file", str(state_file)])
    assert run_runbook_cmd(ns) == 1


def test_list_empty_returns_zero(parser: argparse.ArgumentParser, state_file: Path) -> None:
    ns = parser.parse_args(["runbook", "list", "--state-file", str(state_file)])
    assert run_runbook_cmd(ns) == 0


def test_no_action_returns_nonzero(parser: argparse.ArgumentParser, state_file: Path) -> None:
    ns = parser.parse_args(["runbook", "list", "--state-file", str(state_file)])
    ns.runbook_action = None
    assert run_runbook_cmd(ns) == 1
