"""Tests for cronwatcher.job_priority."""
import pytest

from cronwatcher.config import JobConfig
from cronwatcher.job_priority import (
    Priority,
    PriorityIndex,
    build_priority_index,
)


def _make_job(name: str) -> JobConfig:
    return JobConfig(name=name, schedule="0 * * * *", command=f"echo {name}")


@pytest.fixture()
def jobs():
    return [_make_job(n) for n in ("backup", "report", "cleanup", "ping")]


@pytest.fixture()
def index(jobs):
    return build_priority_index(
        jobs,
        {
            "backup": "critical",
            "report": "high",
            "cleanup": "low",
            # ping gets default NORMAL
        },
    )


def test_priority_from_str_valid():
    assert Priority.from_str("high") == Priority.HIGH
    assert Priority.from_str("CRITICAL") == Priority.CRITICAL


def test_priority_from_str_invalid():
    with pytest.raises(ValueError, match="Unknown priority"):
        Priority.from_str("urgent")


def test_default_priority_is_normal(jobs):
    idx = PriorityIndex()
    for job in jobs:
        assert idx.get(job.name) == Priority.NORMAL


def test_set_and_get(jobs):
    idx = PriorityIndex()
    idx.set(jobs[0].name, Priority.CRITICAL)
    assert idx.get(jobs[0].name) == Priority.CRITICAL


def test_build_priority_index_assigns_correctly(index):
    assert index.get("backup") == Priority.CRITICAL
    assert index.get("report") == Priority.HIGH
    assert index.get("cleanup") == Priority.LOW
    assert index.get("ping") == Priority.NORMAL


def test_sorted_jobs_descending(jobs, index):
    sorted_jobs = index.sorted_jobs(jobs)
    priorities = [index.get(j.name) for j in sorted_jobs]
    assert priorities == sorted(priorities, reverse=True)


def test_sorted_jobs_ascending(jobs, index):
    sorted_jobs = index.sorted_jobs(jobs, descending=False)
    priorities = [index.get(j.name) for j in sorted_jobs]
    assert priorities == sorted(priorities)


def test_jobs_at_returns_matching_only(jobs, index):
    high_jobs = index.jobs_at(jobs, Priority.HIGH)
    assert len(high_jobs) == 1
    assert high_jobs[0].name == "report"


def test_jobs_at_returns_empty_when_none_match(jobs, index):
    result = index.jobs_at(jobs, Priority.LOW)
    assert [j.name for j in result] == ["cleanup"]


def test_unknown_job_name_returns_normal(index):
    assert index.get("nonexistent_job") == Priority.NORMAL
