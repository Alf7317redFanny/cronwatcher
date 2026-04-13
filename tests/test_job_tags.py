"""Tests for cronwatcher.job_tags module."""
import pytest
from cronwatcher.config import JobConfig
from cronwatcher.job_tags import TagIndex


def _make_job(name: str, tags=None) -> JobConfig:
    return JobConfig(
        name=name,
        schedule="* * * * *",
        command=f"echo {name}",
        tags=tags or [],
    )


@pytest.fixture
def jobs():
    return [
        _make_job("backup", ["daily", "critical"]),
        _make_job("report", ["daily", "email"]),
        _make_job("cleanup", ["weekly"]),
        _make_job("ping", []),
    ]


@pytest.fixture
def index(jobs):
    idx = TagIndex()
    idx.build(jobs)
    return idx


def test_all_tags_sorted(index):
    assert index.all_tags() == ["critical", "daily", "email", "weekly"]


def test_jobs_for_tag_daily(index):
    assert set(index.jobs_for_tag("daily")) == {"backup", "report"}


def test_jobs_for_tag_missing(index):
    assert index.jobs_for_tag("nonexistent") == []


def test_tags_for_job(index):
    assert set(index.tags_for_job("backup")) == {"daily", "critical"}


def test_tags_for_untagged_job(index):
    assert index.tags_for_job("ping") == []


def test_filter_jobs_by_single_tag(index, jobs):
    result = index.filter_jobs(jobs, ["weekly"])
    assert len(result) == 1
    assert result[0].name == "cleanup"


def test_filter_jobs_by_multiple_tags(index, jobs):
    result = index.filter_jobs(jobs, ["critical", "email"])
    names = {j.name for j in result}
    assert names == {"backup", "report"}


def test_filter_jobs_empty_tags_returns_all(index, jobs):
    result = index.filter_jobs(jobs, [])
    assert len(result) == len(jobs)


def test_repr(index):
    r = repr(index)
    assert "TagIndex" in r
    assert "daily" in r


def test_rebuild_clears_old_data(jobs):
    idx = TagIndex()
    idx.build(jobs)
    assert "daily" in idx.all_tags()
    idx.build([])
    assert idx.all_tags() == []
