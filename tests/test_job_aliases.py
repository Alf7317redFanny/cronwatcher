"""Tests for cronwatcher.job_aliases."""
import json
import pytest
from pathlib import Path

from cronwatcher.job_aliases import AliasIndex


@pytest.fixture
def alias_path(tmp_path: Path) -> Path:
    return tmp_path / "aliases.json"


@pytest.fixture
def index(alias_path: Path) -> AliasIndex:
    return AliasIndex(_path=alias_path)


# ---------------------------------------------------------------------------
# basic state
# ---------------------------------------------------------------------------

def test_starts_empty(index: AliasIndex) -> None:
    assert index.all_aliases() == {}


def test_load_nonexistent_is_noop(alias_path: Path) -> None:
    idx = AliasIndex(_path=alias_path)
    assert idx.all_aliases() == {}


# ---------------------------------------------------------------------------
# add / resolve
# ---------------------------------------------------------------------------

def test_add_and_resolve(index: AliasIndex) -> None:
    index.add("backup", "db-backup-job")
    assert index.resolve("backup") == "db-backup-job"


def test_resolve_unknown_returns_none(index: AliasIndex) -> None:
    assert index.resolve("nonexistent") is None


def test_add_persists_to_disk(index: AliasIndex, alias_path: Path) -> None:
    index.add("bkp", "db-backup-job")
    raw = json.loads(alias_path.read_text())
    assert raw["aliases"]["bkp"] == "db-backup-job"


def test_add_same_alias_twice_is_idempotent(index: AliasIndex) -> None:
    index.add("bkp", "db-backup-job")
    index.add("bkp", "db-backup-job")  # should not raise
    assert index.resolve("bkp") == "db-backup-job"


def test_add_alias_conflict_raises(index: AliasIndex) -> None:
    index.add("bkp", "db-backup-job")
    with pytest.raises(ValueError, match="already mapped"):
        index.add("bkp", "other-job")


def test_add_blank_alias_raises(index: AliasIndex) -> None:
    with pytest.raises(ValueError, match="alias must not be blank"):
        index.add("  ", "some-job")


def test_add_blank_canonical_raises(index: AliasIndex) -> None:
    with pytest.raises(ValueError, match="canonical job name must not be blank"):
        index.add("bkp", "")


def test_alias_same_as_canonical_raises(index: AliasIndex) -> None:
    with pytest.raises(ValueError, match="must differ"):
        index.add("myjob", "myjob")


# ---------------------------------------------------------------------------
# aliases_for
# ---------------------------------------------------------------------------

def test_aliases_for_returns_all(index: AliasIndex) -> None:
    index.add("bkp", "db-backup-job")
    index.add("backup", "db-backup-job")
    result = sorted(index.aliases_for("db-backup-job"))
    assert result == ["backup", "bkp"]


def test_aliases_for_unknown_canonical_returns_empty(index: AliasIndex) -> None:
    assert index.aliases_for("ghost-job") == []


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------

def test_remove_deletes_alias(index: AliasIndex) -> None:
    index.add("bkp", "db-backup-job")
    index.remove("bkp")
    assert index.resolve("bkp") is None


def test_remove_persists_to_disk(index: AliasIndex, alias_path: Path) -> None:
    index.add("bkp", "db-backup-job")
    index.remove("bkp")
    raw = json.loads(alias_path.read_text())
    assert "bkp" not in raw["aliases"]


def test_remove_unknown_raises(index: AliasIndex) -> None:
    with pytest.raises(KeyError, match="not found"):
        index.remove("ghost")


# ---------------------------------------------------------------------------
# persistence round-trip
# ---------------------------------------------------------------------------

def test_reload_restores_state(alias_path: Path) -> None:
    idx1 = AliasIndex(_path=alias_path)
    idx1.add("bkp", "db-backup-job")
    idx1.add("logs", "log-rotate-job")

    idx2 = AliasIndex(_path=alias_path)
    assert idx2.resolve("bkp") == "db-backup-job"
    assert idx2.resolve("logs") == "log-rotate-job"
