"""Tests for cronwatcher.job_snapshots and snapshot_cli."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pytest

from cronwatcher.job_snapshots import JobSnapshot, SnapshotStore
from cronwatcher.snapshot_cli import add_snapshot_args, run_snapshot_cmd


@pytest.fixture()
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "snapshots.json"


@pytest.fixture()
def store(store_path: Path) -> SnapshotStore:
    return SnapshotStore(store_path)


def _snap(name: str = "backup", status: str = "ok", run: int = 5, fail: int = 0) -> JobSnapshot:
    return JobSnapshot(
        job_name=name,
        timestamp=time.time(),
        last_run=time.time() - 60,
        last_status=status,
        run_count=run,
        failure_count=fail,
    )


def test_store_starts_empty(store: SnapshotStore) -> None:
    assert store.all() == []


def test_record_returns_snapshot(store: SnapshotStore) -> None:
    snap = _snap()
    result = store.record(snap)
    assert result is snap


def test_record_persists_to_disk(store_path: Path, store: SnapshotStore) -> None:
    store.record(_snap())
    reloaded = SnapshotStore(store_path)
    assert len(reloaded.all()) == 1


def test_latest_for_returns_most_recent(store: SnapshotStore) -> None:
    store.record(_snap(run=1))
    store.record(_snap(run=2))
    latest = store.latest_for("backup")
    assert latest is not None
    assert latest.run_count == 2


def test_latest_for_missing_job_returns_none(store: SnapshotStore) -> None:
    assert store.latest_for("ghost") is None


def test_all_for_filters_by_job(store: SnapshotStore) -> None:
    store.record(_snap("backup"))
    store.record(_snap("cleanup"))
    store.record(_snap("backup"))
    assert len(store.all_for("backup")) == 2
    assert len(store.all_for("cleanup")) == 1


def test_diff_returns_none_when_only_one_snapshot(store: SnapshotStore) -> None:
    store.record(_snap())
    assert store.diff("backup") is None


def test_diff_detects_status_change(store: SnapshotStore) -> None:
    store.record(_snap(status="ok", run=3, fail=0))
    store.record(_snap(status="failed", run=4, fail=1))
    diff = store.diff("backup")
    assert diff is not None
    assert "last_status" in diff
    assert diff["last_status"] == {"before": "ok", "after": "failed"}


def test_diff_returns_none_when_no_changes(store: SnapshotStore) -> None:
    snap = _snap()
    store.record(snap)
    store.record(_snap(run=snap.run_count, fail=snap.failure_count, status=snap.last_status))
    # timestamps differ but are not tracked in diff fields — no tracked field changed
    diff = store.diff("backup")
    assert diff is None


def test_snapshot_repr_contains_job_name() -> None:
    snap = _snap(name="myjob")
    assert "myjob" in repr(snap)


def test_roundtrip_serialization() -> None:
    snap = _snap()
    assert JobSnapshot.from_dict(snap.to_dict()) == snap


# --- CLI tests ---


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="command")
    add_snapshot_args(sp)
    return p


def test_cli_take_creates_snapshot(store_path: Path) -> None:
    p = _build_parser()
    args = p.parse_args(["snapshot", "take", "backup",
                         "--last-status", "ok",
                         "--run-count", "7",
                         "--store", str(store_path)])
    rc = run_snapshot_cmd(args)
    assert rc == 0
    store = SnapshotStore(store_path)
    assert store.latest_for("backup") is not None


def test_cli_show_missing_job_returns_nonzero(store_path: Path) -> None:
    p = _build_parser()
    args = p.parse_args(["snapshot", "show", "ghost", "--store", str(store_path)])
    assert run_snapshot_cmd(args) == 1


def test_cli_diff_insufficient_data_returns_nonzero(store_path: Path) -> None:
    store = SnapshotStore(store_path)
    store.record(_snap())
    p = _build_parser()
    args = p.parse_args(["snapshot", "diff", "backup", "--store", str(store_path)])
    assert run_snapshot_cmd(args) == 1
