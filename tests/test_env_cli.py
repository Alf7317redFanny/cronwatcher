"""Tests for cronwatcher.env_cli."""
import argparse
import pytest

from cronwatcher.env_cli import (
    add_env_args,
    parse_env_overrides,
    apply_env_to_index,
    env_summary,
)
from cronwatcher.job_env import EnvIndex


@pytest.fixture()
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    add_env_args(p)
    return p


@pytest.fixture()
def index() -> EnvIndex:
    return EnvIndex()


def test_add_env_args_creates_flag(parser):
    ns = parser.parse_args(["--env", "FOO=bar"])
    assert ns.env_overrides == ["FOO=bar"]


def test_add_env_args_repeatable(parser):
    ns = parser.parse_args(["--env", "A=1", "--env", "B=2"])
    assert set(ns.env_overrides) == {"A=1", "B=2"}


def test_add_env_args_default_empty(parser):
    ns = parser.parse_args([])
    assert ns.env_overrides == []


def test_parse_env_overrides_valid():
    result = parse_env_overrides(["FOO=bar", "X=1"])
    assert result == {"FOO": "bar", "X": "1"}


def test_parse_env_overrides_value_with_equals():
    result = parse_env_overrides(["URL=http://a.com/b=c"])
    assert result["URL"] == "http://a.com/b=c"


def test_parse_env_overrides_missing_equals_raises():
    with pytest.raises(argparse.ArgumentTypeError, match="KEY=VALUE"):
        parse_env_overrides(["NOEQUALSSIGN"])


def test_parse_env_overrides_empty_key_raises():
    with pytest.raises(argparse.ArgumentTypeError, match="empty"):
        parse_env_overrides(["=value"])


def test_apply_env_to_index(index):
    apply_env_to_index(index, "myjob", ["FOO=bar", "BAZ=qux"])
    assert index.get("myjob", "FOO") == "bar"
    assert index.get("myjob", "BAZ") == "qux"


def test_env_summary_no_overrides(index):
    summary = env_summary(index, "myjob")
    assert "no env overrides" in summary


def test_env_summary_with_overrides(index):
    index.set("myjob", "FOO", "bar")
    summary = env_summary(index, "myjob")
    assert "FOO=bar" in summary
    assert "myjob" in summary
