"""Tests for cronwatcher.secrets_cli."""
import argparse
import pytest
from cronwatcher.job_secrets import SecretIndex
from cronwatcher.secrets_cli import (
    add_secrets_args,
    parse_secret_args,
    apply_secrets_to_index,
    secrets_summary,
)


@pytest.fixture
def parser():
    p = argparse.ArgumentParser()
    add_secrets_args(p)
    return p


@pytest.fixture
def index():
    return SecretIndex()


def test_add_secrets_args_creates_flag(parser):
    args = parser.parse_args([])
    assert args.secrets == []


def test_add_secrets_args_single(parser):
    args = parser.parse_args(["--secret", "DB_PASS=vault:db#pw"])
    assert args.secrets == ["DB_PASS=vault:db#pw"]


def test_add_secrets_args_repeatable(parser):
    args = parser.parse_args(
        ["--secret", "DB_PASS=k1", "--secret", "API_KEY=k2"]
    )
    assert len(args.secrets) == 2


def test_parse_secret_args_valid():
    pairs = parse_secret_args(["DB_PASS=vault:db#pw"])
    assert len(pairs) == 1
    env_var, ref = pairs[0]
    assert env_var == "DB_PASS"
    assert ref.key == "vault:db#pw"


def test_parse_secret_args_multiple():
    pairs = parse_secret_args(["A=k1", "B=k2"])
    assert {e for e, _ in pairs} == {"A", "B"}


def test_parse_secret_args_no_equals_raises():
    with pytest.raises(ValueError, match="expected VAR=key"):
        parse_secret_args(["NOEQUALSSIGN"])


def test_parse_secret_args_empty_var_raises():
    with pytest.raises(ValueError, match="Empty env var"):
        parse_secret_args(["=some-key"])


def test_apply_secrets_to_index(index):
    count = apply_secrets_to_index("my-job", ["DB_PASS=k1", "TOKEN=k2"], index)
    assert count == 2
    assert index.get("my-job", "DB_PASS") is not None
    assert index.get("my-job", "TOKEN") is not None


def test_apply_secrets_empty_list(index):
    count = apply_secrets_to_index("my-job", [], index)
    assert count == 0


def test_secrets_summary_no_secrets(index):
    result = secrets_summary("my-job", index)
    assert "no secrets" in result


def test_secrets_summary_with_secrets(index):
    apply_secrets_to_index("my-job", ["DB_PASS=vault:db", "TOKEN=vault:api"], index)
    result = secrets_summary("my-job", index)
    assert "DB_PASS" in result
    assert "TOKEN" in result
    assert "vault:db" in result


def test_secrets_summary_sorted(index):
    apply_secrets_to_index("my-job", ["Z_VAR=k1", "A_VAR=k2"], index)
    result = secrets_summary("my-job", index)
    assert result.index("A_VAR") < result.index("Z_VAR")
