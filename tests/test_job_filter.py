"""Tests for cronwatcher.job_filter."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.job_filter import FilterCriteria, JobFilter
from cronwatcher.scheduler import JobStatus, Scheduler


def _make_job(name: str, tags: list[str] | None = None) -> JobConfig:
    return JobConfig(
        name=name,
        schedule="* * * * *",
        command=f"echo {name}",
        tags=tags or [],
    )


@pytest.fixture()
def jobs() -> list[JobConfig]:
    return [
        _make_job("backup", ["daily", "storage"]),
        _make_job("report", ["daily", "email"]),
        _make_job("cleanup", ["weekly"]),
        _make_job("ping"),
    ]


@pytest.fixture()
def scheduler(jobs: list[JobConfig]) -> Scheduler:
    return Scheduler(jobs)


@pytest.fixture()
def job_filter(jobs: list[JobConfig], scheduler: Scheduler) -> JobFilter:
    return JobFilter(jobs, scheduler)


def test_empty_criteria_returns_all(job_filter: JobFilter, jobs: list[JobConfig]) -> None:
    result = job_filter.apply(FilterCriteria())
    assert len(result) == len(jobs)


def test_filter_by_single_tag(job_filter: JobFilter) -> None:
    result = job_filter.apply(FilterCriteria(tags=["daily"]))
    names = {j.name for j in result}
    assert names == {"backup", "report"}


def test_filter_by_multiple_tags_union(job_filter: JobFilter) -> None:
    result = job_filter.apply(FilterCriteria(tags=["weekly", "email"]))
    names = {j.name for j in result}
    assert names == {"cleanup", "report"}


def test_filter_by_name_contains(job_filter: JobFilter) -> None:
    result = job_filter.apply(FilterCriteria(name_contains="back"))
    assert len(result) == 1
    assert result[0].name == "backup"


def test_filter_by_name_case_insensitive(job_filter: JobFilter) -> None:
    result = job_filter.apply(FilterCriteria(name_contains="BACK"))
    assert len(result) == 1


def test_filter_by_status_unknown(job_filter: JobFilter, jobs: list[JobConfig]) -> None:
    result = job_filter.apply(FilterCriteria(status="unknown"))
    assert len(result) == len(jobs)  # no runs recorded yet


def test_filter_by_status_ok(job_filter: JobFilter, scheduler: Scheduler, jobs: list[JobConfig]) -> None:
    scheduler.record_run(jobs[0].name, success=True)
    result = job_filter.apply(FilterCriteria(status="ok"))
    assert len(result) == 1
    assert result[0].name == "backup"


def test_filter_by_status_failed(job_filter: JobFilter, scheduler: Scheduler, jobs: list[JobConfig]) -> None:
    scheduler.record_run(jobs[1].name, success=False)
    result = job_filter.apply(FilterCriteria(status="failed"))
    assert len(result) == 1
    assert result[0].name == "report"


def test_combined_tag_and_name(job_filter: JobFilter) -> None:
    result = job_filter.apply(FilterCriteria(tags=["daily"], name_contains="rep"))
    assert len(result) == 1
    assert result[0].name == "report"


def test_no_match_returns_empty(job_filter: JobFilter) -> None:
    result = job_filter.apply(FilterCriteria(tags=["nonexistent"]))
    assert result == []
