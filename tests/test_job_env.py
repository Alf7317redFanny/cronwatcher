"""Tests for cronwatcher.job_env."""
import pytest

from cronwatcher.job_env import EnvVar, EnvIndex


# --- EnvVar ---

def test_envvar_valid():
    ev = EnvVar(key="PATH", value="/usr/bin")
    assert ev.key == "PATH"
    assert ev.value == "/usr/bin"


def test_envvar_empty_key_raises():
    with pytest.raises(ValueError, match="empty"):
        EnvVar(key="  ", value="x")


def test_envvar_key_with_equals_raises():
    with pytest.raises(ValueError, match="="):
        EnvVar(key="A=B", value="x")


def test_envvar_repr():
    ev = EnvVar(key="FOO", value="bar")
    assert "FOO" in repr(ev) and "bar" in repr(ev)


# --- EnvIndex ---

@pytest.fixture()
def index() -> EnvIndex:
    return EnvIndex()


def test_get_missing_returns_none(index):
    assert index.get("job1", "MISSING") is None


def test_set_and_get_roundtrip(index):
    index.set("job1", "FOO", "bar")
    assert index.get("job1", "FOO") == "bar"


def test_set_invalid_key_raises(index):
    with pytest.raises(ValueError):
        index.set("job1", "", "value")


def test_all_for_job_empty(index):
    assert index.all_for_job("job1") == {}


def test_all_for_job_returns_copy(index):
    index.set("job1", "X", "1")
    result = index.all_for_job("job1")
    result["X"] = "mutated"
    assert index.get("job1", "X") == "1"


def test_delete_existing_key(index):
    index.set("job1", "FOO", "bar")
    removed = index.delete("job1", "FOO")
    assert removed is True
    assert index.get("job1", "FOO") is None


def test_delete_missing_key_returns_false(index):
    assert index.delete("job1", "NOPE") is False


def test_jobs_with_key(index):
    index.set("job1", "DEBUG", "1")
    index.set("job2", "DEBUG", "0")
    index.set("job3", "OTHER", "x")
    jobs = index.jobs_with_key("DEBUG")
    assert set(jobs) == {"job1", "job2"}


def test_merge_into_overrides_base(index):
    index.set("job1", "FOO", "override")
    base = {"FOO": "base", "BAR": "keep"}
    result = index.merge_into("job1", base)
    assert result["FOO"] == "override"
    assert result["BAR"] == "keep"


def test_merge_into_does_not_mutate_base(index):
    index.set("job1", "X", "new")
    base = {"X": "old"}
    index.merge_into("job1", base)
    assert base["X"] == "old"
