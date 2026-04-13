"""Tests for cronwatcher.group_filter."""
import argparse
import pytest
from cronwatcher.config import JobConfig
from cronwatcher.job_groups import GroupRegistry
from cronwatcher.group_filter import (
    GroupFilter,
    GroupFilterCriteria,
    add_group_filter_args,
    group_criteria_from_args,
)


def _make_job(name: str) -> JobConfig:
    return JobConfig(name=name, schedule="@daily", command=f"echo {name}")


@pytest.fixture
def jobs():
    return [_make_job("alpha"), _make_job("beta"), _make_job("gamma")]


@pytest.fixture
def registry(jobs):
    reg = GroupRegistry()
    reg.assign("critical", jobs[0])
    reg.assign("critical", jobs[1])
    reg.assign("optional", jobs[2])
    return reg


@pytest.fixture
def gfilter(registry):
    return GroupFilter(registry)


def test_empty_criteria_returns_all(gfilter, jobs):
    result = gfilter.apply(jobs, GroupFilterCriteria())
    assert result == jobs


def test_filter_by_group(gfilter, jobs):
    criteria = GroupFilterCriteria(group="critical")
    result = gfilter.apply(jobs, criteria)
    names = [j.name for j in result]
    assert names == ["alpha", "beta"]


def test_filter_by_nonexistent_group_returns_empty(gfilter, jobs):
    criteria = GroupFilterCriteria(group="ghost")
    result = gfilter.apply(jobs, criteria)
    assert result == []


def test_exclude_group(gfilter, jobs):
    criteria = GroupFilterCriteria(exclude_group="critical")
    result = gfilter.apply(jobs, criteria)
    names = [j.name for j in result]
    assert names == ["gamma"]


def test_exclude_nonexistent_group_returns_all(gfilter, jobs):
    criteria = GroupFilterCriteria(exclude_group="ghost")
    result = gfilter.apply(jobs, criteria)
    assert result == jobs


def test_group_and_exclude_combined(gfilter, jobs, registry):
    registry.assign("critical", jobs[2])  # gamma also in critical now
    registry.assign("optional", jobs[0])  # alpha also in optional now
    criteria = GroupFilterCriteria(group="critical", exclude_group="optional")
    result = gfilter.apply(jobs, criteria)
    names = [j.name for j in result]
    assert "beta" in names
    assert "alpha" not in names


def test_criteria_is_empty():
    assert GroupFilterCriteria().is_empty() is True
    assert GroupFilterCriteria(group="x").is_empty() is False
    assert GroupFilterCriteria(exclude_group="x").is_empty() is False


def test_add_group_filter_args():
    parser = argparse.ArgumentParser()
    add_group_filter_args(parser)
    args = parser.parse_args(["--group", "critical", "--exclude-group", "optional"])
    assert args.group == "critical"
    assert args.exclude_group == "optional"


def test_group_criteria_from_args():
    parser = argparse.ArgumentParser()
    add_group_filter_args(parser)
    args = parser.parse_args(["--group", "nightly"])
    criteria = group_criteria_from_args(args)
    assert criteria.group == "nightly"
    assert criteria.exclude_group is None
