import argparse
import pytest
from pathlib import Path
from cronwatcher.pause_cli import add_pause_args, run_pause_cmd


@pytest.fixture
def parser():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command")
    add_pause_args(sub)
    return p


@pytest.fixture
def state_file(tmp_path) -> Path:
    return tmp_path / "pause.json"


def _args(parser, argv):
    return parser.parse_args(argv)


def test_add_pause_args_registers_subcommand(parser):
    ns = _args(parser, ["pause", "list", "--state-file", "/tmp/x.json"])
    assert ns.command == "pause"


def test_pause_add_returns_zero(parser, state_file, capsys):
    ns = _args(parser, ["pause", "add", "backup", "--reason", "maint", "--state-file", str(state_file)])
    result = run_pause_cmd(ns)
    assert result == 0
    out = capsys.readouterr().out
    assert "backup" in out


def test_pause_list_empty(parser, state_file, capsys):
    ns = _args(parser, ["pause", "list", "--state-file", str(state_file)])
    run_pause_cmd(ns)
    out = capsys.readouterr().out
    assert "No jobs" in out


def test_pause_list_shows_paused(parser, state_file, capsys):
    ns_add = _args(parser, ["pause", "add", "sync", "--state-file", str(state_file)])
    run_pause_cmd(ns_add)
    ns_list = _args(parser, ["pause", "list", "--state-file", str(state_file)])
    run_pause_cmd(ns_list)
    out = capsys.readouterr().out
    assert "sync" in out


def test_pause_remove_returns_zero(parser, state_file, capsys):
    ns_add = _args(parser, ["pause", "add", "sync", "--state-file", str(state_file)])
    run_pause_cmd(ns_add)
    ns_rm = _args(parser, ["pause", "remove", "sync", "--state-file", str(state_file)])
    result = run_pause_cmd(ns_rm)
    assert result == 0


def test_pause_remove_unknown_still_zero(parser, state_file, capsys):
    ns = _args(parser, ["pause", "remove", "ghost", "--state-file", str(state_file)])
    result = run_pause_cmd(ns)
    assert result == 0
    assert "not paused" in capsys.readouterr().out
