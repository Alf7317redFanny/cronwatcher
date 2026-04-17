"""Tests for notes CLI helpers."""
import argparse
import pytest
from pathlib import Path
from cronwatcher.notes_cli import add_notes_args, run_notes_cmd


@pytest.fixture
def parser():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command")
    add_notes_args(sub)
    return p


@pytest.fixture
def notes_file(tmp_path) -> str:
    return str(tmp_path / "notes.json")


def _args(parser, notes_file, *extra):
    return parser.parse_args(["notes", *extra, "--notes-file", notes_file])


def test_add_notes_args_registers_subcommand(parser):
    args = parser.parse_args(["notes", "list", "myjob", "--notes-file", "/tmp/n.json"])
    assert args.command == "notes"


def test_add_action_returns_zero(parser, notes_file):
    args = _args(parser, notes_file, "add", "backup", "--text", "check logs")
    assert run_notes_cmd(args) == 0


def test_add_without_text_returns_one(parser, notes_file, capsys):
    args = _args(parser, notes_file, "add", "backup")
    result = run_notes_cmd(args)
    assert result == 1
    assert "--text" in capsys.readouterr().out


def test_list_empty_job(parser, notes_file, capsys):
    args = _args(parser, notes_file, "list", "backup")
    result = run_notes_cmd(args)
    assert result == 0
    assert "No notes" in capsys.readouterr().out


def test_list_shows_notes(parser, notes_file, capsys):
    add_args = _args(parser, notes_file, "add", "backup", "--text", "important")
    run_notes_cmd(add_args)
    list_args = _args(parser, notes_file, "list", "backup")
    run_notes_cmd(list_args)
    assert "important" in capsys.readouterr().out


def test_clear_removes_notes(parser, notes_file, capsys):
    run_notes_cmd(_args(parser, notes_file, "add", "sync", "--text", "note"))
    result = run_notes_cmd(_args(parser, notes_file, "clear", "sync"))
    assert result == 0
    capsys.readouterr()
    run_notes_cmd(_args(parser, notes_file, "list", "sync"))
    assert "No notes" in capsys.readouterr().out
