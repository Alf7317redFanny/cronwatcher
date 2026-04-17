"""Tests for NoteIndex."""
import pytest
from pathlib import Path
from cronwatcher.job_notes import NoteEntry, NoteIndex


@pytest.fixture
def notes_path(tmp_path) -> Path:
    return tmp_path / "notes.json"


@pytest.fixture
def index(notes_path) -> NoteIndex:
    return NoteIndex(notes_path)


def test_starts_empty(index):
    assert index.get("backup") == []


def test_add_returns_entry(index):
    e = index.add("backup", "runs nightly", "2024-01-01T00:00:00+00:00")
    assert isinstance(e, NoteEntry)
    assert e.job_name == "backup"
    assert e.text == "runs nightly"


def test_get_returns_added_notes(index):
    index.add("backup", "first note", "2024-01-01T00:00:00+00:00")
    index.add("backup", "second note", "2024-01-02T00:00:00+00:00")
    notes = index.get("backup")
    assert len(notes) == 2
    assert notes[0].text == "first note"
    assert notes[1].text == "second note"


def test_notes_persisted_across_instances(notes_path):
    idx1 = NoteIndex(notes_path)
    idx1.add("deploy", "check logs", "2024-01-01T00:00:00+00:00")
    idx2 = NoteIndex(notes_path)
    assert len(idx2.get("deploy")) == 1


def test_delete_all_removes_notes(index):
    index.add("sync", "note a", "2024-01-01T00:00:00+00:00")
    index.add("sync", "note b", "2024-01-02T00:00:00+00:00")
    removed = index.delete_all("sync")
    assert removed == 2
    assert index.get("sync") == []


def test_delete_all_missing_job_returns_zero(index):
    assert index.delete_all("nonexistent") == 0


def test_all_jobs_with_notes(index):
    index.add("jobA", "note", "2024-01-01T00:00:00+00:00")
    index.add("jobB", "note", "2024-01-01T00:00:00+00:00")
    jobs = index.all_jobs_with_notes()
    assert "jobA" in jobs
    assert "jobB" in jobs


def test_note_repr():
    e = NoteEntry("myjob", "hello world", "2024-01-01T00:00:00+00:00")
    assert "myjob" in repr(e)


def test_note_roundtrip_dict():
    e = NoteEntry("j", "text", "ts")
    assert NoteEntry.from_dict(e.to_dict()) == e


def test_load_nonexistent_file_is_noop(tmp_path):
    idx = NoteIndex(tmp_path / "missing.json")
    assert idx.get("x") == []
