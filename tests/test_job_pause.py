import pytest
from pathlib import Path
from cronwatcher.job_pause import PauseIndex, PauseRecord


@pytest.fixture
def pause_path(tmp_path) -> Path:
    return tmp_path / "pause.json"


@pytest.fixture
def index(pause_path) -> PauseIndex:
    return PauseIndex(pause_path)


def test_starts_empty(index):
    assert index.all_paused() == []


def test_pause_returns_record(index):
    r = index.pause("backup", reason="maintenance")
    assert isinstance(r, PauseRecord)
    assert r.job_name == "backup"
    assert r.reason == "maintenance"


def test_is_paused_after_pause(index):
    index.pause("backup")
    assert index.is_paused("backup") is True


def test_is_not_paused_initially(index):
    assert index.is_paused("backup") is False


def test_resume_returns_true(index):
    index.pause("backup")
    assert index.resume("backup") is True


def test_resume_unknown_returns_false(index):
    assert index.resume("ghost") is False


def test_is_not_paused_after_resume(index):
    index.pause("backup")
    index.resume("backup")
    assert index.is_paused("backup") is False


def test_all_paused_lists_multiple(index):
    index.pause("a")
    index.pause("b")
    names = {r.job_name for r in index.all_paused()}
    assert names == {"a", "b"}


def test_persists_to_disk(pause_path):
    idx1 = PauseIndex(pause_path)
    idx1.pause("sync", reason="testing")
    idx2 = PauseIndex(pause_path)
    assert idx2.is_paused("sync")
    assert idx2.all_paused()[0].reason == "testing"


def test_repr():
    r = PauseRecord("myjob", "no reason")
    assert "myjob" in repr(r)
    assert "no reason" in repr(r)
