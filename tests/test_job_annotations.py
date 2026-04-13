"""Tests for cronwatcher.job_annotations."""
import pytest

from cronwatcher.config import JobConfig
from cronwatcher.job_annotations import AnnotationIndex


def _make_job(name: str) -> JobConfig:
    return JobConfig(name=name, schedule="@daily", command=f"echo {name}")


@pytest.fixture()
def jobs():
    return [_make_job("backup"), _make_job("report"), _make_job("cleanup")]


@pytest.fixture()
def index():
    return AnnotationIndex()


def test_get_missing_returns_none(jobs, index):
    assert index.get(jobs[0], "owner") is None


def test_set_and_get_roundtrip(jobs, index):
    index.set(jobs[0], "owner", "alice")
    assert index.get(jobs[0], "owner") == "alice"


def test_overwrite_existing(jobs, index):
    index.set(jobs[0], "env", "staging")
    index.set(jobs[0], "env", "production")
    assert index.get(jobs[0], "env") == "production"


def test_empty_key_raises(jobs, index):
    with pytest.raises(ValueError):
        index.set(jobs[0], "", "value")


def test_all_for_job_empty(jobs, index):
    assert index.all_for_job(jobs[0]) == {}


def test_all_for_job_returns_copy(jobs, index):
    index.set(jobs[0], "team", "ops")
    index.set(jobs[0], "tier", "critical")
    result = index.all_for_job(jobs[0])
    assert result == {"team": "ops", "tier": "critical"}
    # mutating the copy should not affect the index
    result["team"] = "dev"
    assert index.get(jobs[0], "team") == "ops"


def test_jobs_with_key(jobs, index):
    index.set(jobs[0], "owner", "alice")
    index.set(jobs[1], "owner", "bob")
    result = set(index.jobs_with_key("owner"))
    assert result == {"backup", "report"}


def test_jobs_with_key_none_match(jobs, index):
    assert list(index.jobs_with_key("nonexistent")) == []


def test_jobs_with_annotation(jobs, index):
    index.set(jobs[0], "env", "prod")
    index.set(jobs[1], "env", "staging")
    index.set(jobs[2], "env", "prod")
    result = set(index.jobs_with_annotation("env", "prod"))
    assert result == {"backup", "cleanup"}


def test_remove_existing(jobs, index):
    index.set(jobs[0], "note", "temporary")
    removed = index.remove(jobs[0], "note")
    assert removed is True
    assert index.get(jobs[0], "note") is None


def test_remove_nonexistent_returns_false(jobs, index):
    assert index.remove(jobs[0], "ghost") is False


def test_clear_removes_all(jobs, index):
    index.set(jobs[0], "a", "1")
    index.set(jobs[0], "b", "2")
    index.clear(jobs[0])
    assert index.all_for_job(jobs[0]) == {}


def test_clear_unregistered_job_is_noop(jobs, index):
    index.clear(jobs[1])  # never annotated — should not raise
