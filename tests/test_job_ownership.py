"""Tests for cronwatcher.job_ownership."""
import json
import pytest
from pathlib import Path

from cronwatcher.job_ownership import OwnerRecord, OwnershipIndex


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "ownership.json"


@pytest.fixture
def index(state_file: Path) -> OwnershipIndex:
    return OwnershipIndex(state_file=state_file)


def test_starts_empty(index: OwnershipIndex) -> None:
    assert index.all_records() == []


def test_set_and_get_roundtrip(index: OwnershipIndex) -> None:
    rec = index.set("backup", "alice", team="ops")
    assert rec.job_name == "backup"
    assert rec.owner == "alice"
    assert rec.team == "ops"
    fetched = index.get("backup")
    assert fetched == rec


def test_get_missing_returns_none(index: OwnershipIndex) -> None:
    assert index.get("nonexistent") is None


def test_set_blank_owner_raises(index: OwnershipIndex) -> None:
    with pytest.raises(ValueError, match="owner must not be blank"):
        index.set("myjob", "   ")


def test_owner_stripped(index: OwnershipIndex) -> None:
    rec = index.set("cleanup", "  bob  ")
    assert rec.owner == "bob"


def test_remove_clears_record(index: OwnershipIndex) -> None:
    index.set("job1", "carol")
    index.remove("job1")
    assert index.get("job1") is None


def test_remove_nonexistent_is_noop(index: OwnershipIndex) -> None:
    index.remove("ghost")  # should not raise


def test_jobs_for_owner(index: OwnershipIndex) -> None:
    index.set("job_a", "alice")
    index.set("job_b", "bob")
    index.set("job_c", "alice")
    assert sorted(index.jobs_for_owner("alice")) == ["job_a", "job_c"]
    assert index.jobs_for_owner("bob") == ["job_b"]


def test_jobs_for_team(index: OwnershipIndex) -> None:
    index.set("job_x", "alice", team="ops")
    index.set("job_y", "bob", team="dev")
    index.set("job_z", "carol", team="ops")
    assert sorted(index.jobs_for_team("ops")) == ["job_x", "job_z"]


def test_persists_to_disk(state_file: Path) -> None:
    idx = OwnershipIndex(state_file=state_file)
    idx.set("persist_job", "dave", team="infra")
    idx2 = OwnershipIndex(state_file=state_file)
    rec = idx2.get("persist_job")
    assert rec is not None
    assert rec.owner == "dave"
    assert rec.team == "infra"


def test_repr_with_team() -> None:
    rec = OwnerRecord(job_name="myjob", owner="eve", team="platform")
    assert "eve" in repr(rec)
    assert "platform" in repr(rec)


def test_repr_without_team() -> None:
    rec = OwnerRecord(job_name="myjob", owner="frank")
    r = repr(rec)
    assert "frank" in r
    assert "team" not in r


def test_all_records_returns_list(index: OwnershipIndex) -> None:
    index.set("j1", "u1")
    index.set("j2", "u2")
    recs = index.all_records()
    assert len(recs) == 2
