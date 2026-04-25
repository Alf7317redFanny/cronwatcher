"""Tests for cronwatcher.job_runbook."""
import json
import pytest
from pathlib import Path
from cronwatcher.job_runbook import RunbookEntry, RunbookIndex


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "runbooks.json"


@pytest.fixture
def index(state_file: Path) -> RunbookIndex:
    return RunbookIndex(state_file)


def test_starts_empty(index: RunbookIndex) -> None:
    assert index.all() == []


def test_load_nonexistent_is_noop(tmp_path: Path) -> None:
    idx = RunbookIndex(tmp_path / "missing.json")
    assert idx.all() == []


def test_set_returns_entry(index: RunbookIndex) -> None:
    e = index.set("backup", url="https://wiki/backup", steps=["check disk"])
    assert e.job_name == "backup"
    assert e.url == "https://wiki/backup"
    assert e.steps == ["check disk"]


def test_get_returns_none_for_unknown(index: RunbookIndex) -> None:
    assert index.get("ghost") is None


def test_get_returns_set_entry(index: RunbookIndex) -> None:
    index.set("sync", url="https://wiki/sync")
    e = index.get("sync")
    assert e is not None
    assert e.url == "https://wiki/sync"


def test_persists_to_disk(index: RunbookIndex, state_file: Path) -> None:
    index.set("deploy", url="https://wiki/deploy", steps=["rollback"])
    raw = json.loads(state_file.read_text())
    assert "deploy" in raw
    assert raw["deploy"]["url"] == "https://wiki/deploy"


def test_roundtrip_reload(state_file: Path) -> None:
    idx1 = RunbookIndex(state_file)
    idx1.set("etl", steps=["step1", "step2"])
    idx2 = RunbookIndex(state_file)
    e = idx2.get("etl")
    assert e is not None
    assert e.steps == ["step1", "step2"]


def test_remove_existing(index: RunbookIndex) -> None:
    index.set("cleanup")
    assert index.remove("cleanup") is True
    assert index.get("cleanup") is None


def test_remove_missing_returns_false(index: RunbookIndex) -> None:
    assert index.remove("nonexistent") is False


def test_all_returns_all_entries(index: RunbookIndex) -> None:
    index.set("job_a")
    index.set("job_b", url="https://x")
    names = {e.job_name for e in index.all()}
    assert names == {"job_a", "job_b"}


def test_repr_no_url() -> None:
    e = RunbookEntry(job_name="x")
    assert "x" in repr(e)
    assert "url" not in repr(e)


def test_repr_with_url() -> None:
    e = RunbookEntry(job_name="x", url="https://wiki")
    assert "url=" in repr(e)


def test_from_dict_roundtrip() -> None:
    e = RunbookEntry(job_name="j", url="https://u", steps=["a", "b"])
    assert RunbookEntry.from_dict(e.to_dict()) == e
