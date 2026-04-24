"""Tests for cronwatcher.job_checksum."""
import json
from pathlib import Path

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.job_checksum import ChecksumIndex, ChecksumRecord, compute_checksum


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_job(name: str = "backup", command: str = "/usr/bin/backup.sh") -> JobConfig:
    return JobConfig(name=name, schedule="@daily", command=command)


@pytest.fixture()
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "checksums.json"


@pytest.fixture()
def index(state_file: Path) -> ChecksumIndex:
    return ChecksumIndex(state_file)


# ---------------------------------------------------------------------------
# compute_checksum
# ---------------------------------------------------------------------------

def test_compute_checksum_is_deterministic():
    job = _make_job()
    assert compute_checksum(job) == compute_checksum(job)


def test_compute_checksum_differs_for_different_commands():
    j1 = _make_job(command="/bin/foo")
    j2 = _make_job(command="/bin/bar")
    assert compute_checksum(j1) != compute_checksum(j2)


def test_compute_checksum_length():
    # SHA-256 hex digest is always 64 chars
    assert len(compute_checksum(_make_job())) == 64


# ---------------------------------------------------------------------------
# ChecksumRecord
# ---------------------------------------------------------------------------

def test_record_roundtrip():
    rec = ChecksumRecord(job_name="nightly", checksum="abc123")
    assert ChecksumRecord.from_dict(rec.to_dict()) == rec


def test_record_repr_truncates_checksum():
    rec = ChecksumRecord(job_name="x", checksum="abcdef1234567890")
    assert "abcdef12" in repr(rec)
    assert "abcdef1234567890" not in repr(rec)


# ---------------------------------------------------------------------------
# ChecksumIndex
# ---------------------------------------------------------------------------

def test_starts_empty(index: ChecksumIndex):
    assert index.all_records() == []


def test_get_missing_returns_none(index: ChecksumIndex):
    assert index.get("nonexistent") is None


def test_record_stores_and_returns(index: ChecksumIndex):
    job = _make_job()
    rec = index.record(job)
    assert rec.job_name == job.name
    assert rec.checksum == compute_checksum(job)


def test_record_persists_to_disk(state_file: Path, index: ChecksumIndex):
    job = _make_job()
    index.record(job)
    data = json.loads(state_file.read_text())
    assert len(data) == 1
    assert data[0]["job_name"] == job.name


def test_load_restores_records(state_file: Path):
    job = _make_job()
    idx1 = ChecksumIndex(state_file)
    idx1.record(job)

    idx2 = ChecksumIndex(state_file)
    assert idx2.get(job.name) is not None


def test_has_changed_false_when_unseen(index: ChecksumIndex):
    job = _make_job()
    assert index.has_changed(job) is False


def test_has_changed_false_when_same(index: ChecksumIndex):
    job = _make_job()
    index.record(job)
    assert index.has_changed(job) is False


def test_has_changed_true_after_command_update(state_file: Path):
    job_v1 = _make_job(command="/bin/v1")
    idx = ChecksumIndex(state_file)
    idx.record(job_v1)

    job_v2 = _make_job(command="/bin/v2")  # same name, different command
    assert idx.has_changed(job_v2) is True


def test_all_records_returns_all(index: ChecksumIndex):
    for name in ("alpha", "beta", "gamma"):
        index.record(_make_job(name=name, command=f"/bin/{name}"))
    names = {r.job_name for r in index.all_records()}
    assert names == {"alpha", "beta", "gamma"}
