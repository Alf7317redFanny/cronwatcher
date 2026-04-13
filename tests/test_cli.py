"""Tests for the CLI entry point."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.cli import build_parser, main


SAMPLE_CONFIG = {
    "jobs": [
        {"name": "backup", "schedule": "0 2 * * *", "command": "echo backup"}
    ],
    "history_path": "/tmp/cronwatcher_test_history.json",
    "notifier": None,
}


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    cfg = tmp_path / "cronwatcher.json"
    cfg.write_text(json.dumps(SAMPLE_CONFIG))
    return cfg


def test_parser_run_command(config_file: Path):
    parser = build_parser()
    args = parser.parse_args(["--config", str(config_file), "run"])
    assert args.command == "run"
    assert args.config == config_file


def test_parser_check_command(config_file: Path):
    parser = build_parser()
    args = parser.parse_args(["--config", str(config_file), "check"])
    assert args.command == "check"


def test_parser_history_defaults(config_file: Path):
    parser = build_parser()
    args = parser.parse_args(["--config", str(config_file), "history"])
    assert args.command == "history"
    assert args.job is None
    assert args.limit == 20


def test_parser_history_with_options(config_file: Path):
    parser = build_parser()
    args = parser.parse_args(
        ["--config", str(config_file), "history", "--job", "backup", "--limit", "5"]
    )
    assert args.job == "backup"
    assert args.limit == 5


def test_main_missing_config(tmp_path: Path):
    missing = tmp_path / "missing.json"
    result = main(["--config", str(missing), "run"])
    assert result == 1


@patch("cronwatcher.cli.cmd_run", return_value=0)
def test_main_dispatches_run(mock_run, config_file: Path):
    result = main(["--config", str(config_file), "run"])
    assert result == 0
    mock_run.assert_called_once_with(config_file)


@patch("cronwatcher.cli.cmd_check", return_value=0)
def test_main_dispatches_check(mock_check, config_file: Path):
    result = main(["--config", str(config_file), "check"])
    assert result == 0
    mock_check.assert_called_once_with(config_file)


@patch("cronwatcher.cli.cmd_history", return_value=0)
def test_main_dispatches_history(mock_history, config_file: Path):
    result = main(["--config", str(config_file), "history", "--job", "backup", "--limit", "10"])
    assert result == 0
    mock_history.assert_called_once_with(config_file, "backup", 10)
