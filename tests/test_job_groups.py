"""Tests for cronwatcher.job_groups."""
import pytest
from cronwatcher.config import JobConfig
from cronwatcher.job_groups import JobGroup, GroupRegistry


def _make_job(name: str, schedule: str = "@hourly") -> JobConfig:
    return JobConfig(name=name, schedule=schedule, command=f"echo {name}")


@pytest.fixture
def registry() -> GroupRegistry:
    return GroupRegistry()


@pytest.fixture
def jobs():
    return [_make_job("backup"), _make_job("cleanup"), _make_job("report")]


def test_create_group(registry):
    group = registry.create("critical")
    assert group.name == "critical"
    assert group.jobs == []


def test_create_duplicate_raises(registry):
    registry.create("critical")
    with pytest.raises(ValueError, match="already exists"):
        registry.create("critical")


def test_get_nonexistent_returns_none(registry):
    assert registry.get("missing") is None


def test_get_or_create_creates_new(registry):
    group = registry.get_or_create("nightly")
    assert group.name == "nightly"


def test_get_or_create_returns_existing(registry):
    g1 = registry.get_or_create("nightly")
    g2 = registry.get_or_create("nightly")
    assert g1 is g2


def test_assign_adds_job(registry, jobs):
    registry.assign("daily", jobs[0])
    group = registry.get("daily")
    assert jobs[0] in group.jobs


def test_assign_no_duplicates(registry, jobs):
    registry.assign("daily", jobs[0])
    registry.assign("daily", jobs[0])
    assert len(registry.get("daily").jobs) == 1


def test_unassign_removes_job(registry, jobs):
    registry.assign("daily", jobs[0])
    registry.unassign("daily", jobs[0].name)
    assert registry.get("daily").jobs == []


def test_unassign_nonexistent_group_is_noop(registry, jobs):
    registry.unassign("ghost", "backup")  # should not raise


def test_groups_for_job(registry, jobs):
    registry.assign("alpha", jobs[0])
    registry.assign("beta", jobs[0])
    result = registry.groups_for_job(jobs[0].name)
    assert sorted(result) == ["alpha", "beta"]


def test_groups_for_job_not_assigned(registry, jobs):
    assert registry.groups_for_job(jobs[0].name) == []


def test_all_group_names_sorted(registry):
    registry.create("zeta")
    registry.create("alpha")
    registry.create("mu")
    assert registry.all_group_names() == ["alpha", "mu", "zeta"]


def test_job_group_repr():
    group = JobGroup(name="test")
    assert "test" in repr(group)
    assert "0" in repr(group)


def test_build_from_tags_skips_no_tags(registry, jobs):
    registry.build_from_tags(jobs)
    assert registry.all_group_names() == []
