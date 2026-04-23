"""Tests for cronwatcher.notifications_cli."""
import argparse
import pytest
from pathlib import Path
from cronwatcher.notifications_cli import add_notifications_args, run_notifications_cmd
from cronwatcher.job_notifications import NotificationIndex, NotificationPrefs


@pytest.fixture
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command")
    add_notifications_args(sub)
    return p


@pytest.fixture
def state_file(tmp_path: Path) -> str:
    return str(tmp_path / "notif.json")


def _args(parser, argv, state_file):
    ns = parser.parse_args(argv)
    ns.state_file = state_file
    return ns


def test_add_notifications_args_registers_subcommand(parser):
    ns = parser.parse_args(["notifications", "list"])
    assert ns.command == "notifications"


def test_set_action_returns_zero(parser, state_file):
    ns = _args(parser, ["notifications", "set", "myjob", "--channels", "email"], state_file)
    assert run_notifications_cmd(ns) == 0


def test_set_persists_preferences(parser, state_file):
    ns = _args(parser, ["notifications", "set", "myjob", "--channels", "slack",
                        "--no-on-missed"], state_file)
    run_notifications_cmd(ns)
    index = NotificationIndex(state_file=state_file)
    prefs = index.get("myjob")
    assert "slack" in prefs.channels
    assert prefs.on_missed is False


def test_get_action_returns_zero(parser, state_file, capsys):
    idx = NotificationIndex(state_file=state_file)
    idx.set("myjob", NotificationPrefs(channels=["webhook"]))
    ns = _args(parser, ["notifications", "get", "myjob"], state_file)
    rc = run_notifications_cmd(ns)
    assert rc == 0
    out = capsys.readouterr().out
    assert "webhook" in out


def test_list_empty_returns_zero(parser, state_file, capsys):
    ns = _args(parser, ["notifications", "list"], state_file)
    rc = run_notifications_cmd(ns)
    assert rc == 0
    assert "No notification" in capsys.readouterr().out


def test_list_shows_jobs(parser, state_file, capsys):
    idx = NotificationIndex(state_file=state_file)
    idx.set("alpha", NotificationPrefs(channels=["email"]))
    idx.set("beta", NotificationPrefs(channels=["log"]))
    ns = _args(parser, ["notifications", "list"], state_file)
    run_notifications_cmd(ns)
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "beta" in out


def test_no_action_returns_one(parser, state_file):
    ns = parser.parse_args(["notifications"])
    ns.state_file = state_file
    ns.notif_action = None
    assert run_notifications_cmd(ns) == 1
