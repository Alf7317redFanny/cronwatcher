"""Tests for job_labels and label_filter."""
import pytest

from cronwatcher.config import JobConfig
from cronwatcher.job_labels import LabelIndex, build
from cronwatcher.label_filter import LabelFilter, LabelFilterCriteria


def _make_job(name: str) -> JobConfig:
    return JobConfig(name=name, schedule="@daily", command=f"echo {name}")


@pytest.fixture()
def jobs():
    return [_make_job("backup"), _make_job("report"), _make_job("cleanup")]


@pytest.fixture()
def index(jobs):
    idx = LabelIndex()
    idx.set(jobs[0], "env", "prod")
    idx.set(jobs[0], "team", "ops")
    idx.set(jobs[1], "env", "staging")
    idx.set(jobs[1], "team", "data")
    idx.set(jobs[2], "env", "prod")
    return idx


# --- LabelIndex tests ---

def test_get_existing_label(jobs, index):
    assert index.get(jobs[0], "env") == "prod"


def test_get_missing_label_returns_none(jobs, index):
    assert index.get(jobs[2], "team") is None


def test_labels_for_job(jobs, index):
    labels = index.labels_for_job(jobs[0])
    assert labels == {"env": "prod", "team": "ops"}


def test_jobs_with_label_key_only(jobs, index):
    result = index.jobs_with_label("env")
    assert result == ["backup", "cleanup", "report"]


def test_jobs_with_label_key_and_value(jobs, index):
    result = index.jobs_with_label("env", "prod")
    assert result == ["backup", "cleanup"]


def test_remove_label(jobs, index):
    index.remove(jobs[0], "team")
    assert index.get(jobs[0], "team") is None


def test_remove_nonexistent_is_noop(jobs, index):
    index.remove(jobs[2], "nonexistent")  # should not raise


def test_all_label_keys(jobs, index):
    assert index.all_label_keys() == ["env", "team"]


def test_empty_key_raises(jobs):
    idx = LabelIndex()
    with pytest.raises(ValueError):
        idx.set(jobs[0], "", "value")


def test_build_from_dict(jobs):
    data = {"backup": {"env": "prod"}, "report": {"env": "staging"}}
    idx = build(jobs, data)
    assert idx.get(jobs[0], "env") == "prod"
    assert idx.get(jobs[1], "env") == "staging"


def test_build_skips_unknown_jobs(jobs):
    data = {"ghost": {"env": "prod"}}
    idx = build(jobs, data)  # should not raise
    assert idx.all_label_keys() == []


# --- LabelFilter tests ---

@pytest.fixture()
def lfilter(index):
    return LabelFilter(index)


def test_empty_criteria_returns_all(jobs, lfilter):
    result = lfilter.apply(jobs, LabelFilterCriteria())
    assert result == jobs


def test_filter_by_key_and_value(jobs, lfilter):
    criteria = LabelFilterCriteria(required={"env": "prod"})
    result = lfilter.apply(jobs, criteria)
    assert [j.name for j in result] == ["backup", "cleanup"]


def test_filter_by_key_any_value(jobs, lfilter):
    criteria = LabelFilterCriteria(required={"team": None})
    result = lfilter.apply(jobs, criteria)
    assert {j.name for j in result} == {"backup", "report"}


def test_filter_no_match(jobs, lfilter):
    criteria = LabelFilterCriteria(required={"env": "dev"})
    result = lfilter.apply(jobs, criteria)
    assert result == []
