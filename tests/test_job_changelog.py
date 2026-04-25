"""Tests for cronwatcher.job_changelog."""
import json
from pathlib import Path

import pytest

from cronwatcher.job_changelog import ChangelogEntry, ChangelogIndex


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "changelog.json"


@pytest.fixture
def index(state_file: Path) -> ChangelogIndex:
    return ChangelogIndex(state_file)


def test_starts_empty(index: ChangelogIndex) -> None:
    assert index.all() == []


def test_load_nonexistent_is_noop(tmp_path: Path) -> None:
    idx = ChangelogIndex(tmp_path / "missing.json")
    assert idx.all() == []


def test_record_returns_entry(index: ChangelogIndex) -> None:
    entry = index.record("backup", "schedule", "@daily", "@hourly")
    assert isinstance(entry, ChangelogEntry)
    assert entry.job_name == "backup"
    assert entry.field == "schedule"
    assert entry.old_value == "@daily"
    assert entry.new_value == "@hourly"


def test_record_persists_to_disk(index: ChangelogIndex, state_file: Path) -> None:
    index.record("backup", "command", "old.sh", "new.sh")
    raw = json.loads(state_file.read_text())
    assert len(raw) == 1
    assert raw[0]["field"] == "command"


def test_for_job_filters_correctly(index: ChangelogIndex) -> None:
    index.record("backup", "schedule", "@daily", "@hourly")
    index.record("cleanup", "schedule", "@weekly", "@daily")
    index.record("backup", "command", "a.sh", "b.sh")

    results = index.for_job("backup")
    assert len(results) == 2
    assert all(e.job_name == "backup" for e in results)


def test_for_job_returns_empty_for_unknown(index: ChangelogIndex) -> None:
    index.record("backup", "schedule", "@daily", "@hourly")
    assert index.for_job("nonexistent") == []


def test_all_returns_every_entry(index: ChangelogIndex) -> None:
    index.record("a", "schedule", None, "@daily")
    index.record("b", "command", "old", "new")
    assert len(index.all()) == 2


def test_fields_changed_counts(index: ChangelogIndex) -> None:
    index.record("backup", "schedule", "@daily", "@hourly")
    index.record("backup", "schedule", "@hourly", "@weekly")
    index.record("backup", "command", "a.sh", "b.sh")

    counts = index.fields_changed("backup")
    assert counts["schedule"] == 2
    assert counts["command"] == 1


def test_fields_changed_empty_for_unknown(index: ChangelogIndex) -> None:
    assert index.fields_changed("ghost") == {}


def test_entry_repr(index: ChangelogIndex) -> None:
    entry = index.record("myjob", "schedule", "old", "new")
    r = repr(entry)
    assert "myjob" in r
    assert "schedule" in r
    assert "old" in r
    assert "new" in r


def test_reload_from_disk(state_file: Path) -> None:
    idx1 = ChangelogIndex(state_file)
    idx1.record("job1", "schedule", "@daily", "@hourly")

    idx2 = ChangelogIndex(state_file)
    entries = idx2.all()
    assert len(entries) == 1
    assert entries[0].job_name == "job1"
    assert entries[0].field == "schedule"


def test_none_values_roundtrip(state_file: Path) -> None:
    idx = ChangelogIndex(state_file)
    idx.record("job", "schedule", None, "@daily")

    idx2 = ChangelogIndex(state_file)
    entry = idx2.all()[0]
    assert entry.old_value is None
    assert entry.new_value == "@daily"
