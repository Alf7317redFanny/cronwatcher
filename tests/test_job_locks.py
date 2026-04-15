"""Tests for cronwatcher.job_locks."""
import os
import time
import pytest
from pathlib import Path

from cronwatcher.job_locks import JobLockManager, LockInfo, LockError


@pytest.fixture
def lock_dir(tmp_path: Path) -> Path:
    return tmp_path / "locks"


@pytest.fixture
def manager(lock_dir: Path) -> JobLockManager:
    return JobLockManager(lock_dir=lock_dir)


def test_lock_dir_created(lock_dir: Path) -> None:
    JobLockManager(lock_dir=lock_dir)
    assert lock_dir.exists()


def test_acquire_returns_lock_info(manager: JobLockManager) -> None:
    info = manager.acquire("backup")
    assert isinstance(info, LockInfo)
    assert info.job_name == "backup"
    assert info.pid == os.getpid()


def test_is_locked_after_acquire(manager: JobLockManager) -> None:
    assert not manager.is_locked("backup")
    manager.acquire("backup")
    assert manager.is_locked("backup")


def test_acquire_twice_raises(manager: JobLockManager) -> None:
    manager.acquire("backup")
    with pytest.raises(LockError, match="backup"):
        manager.acquire("backup")


def test_release_removes_lock(manager: JobLockManager) -> None:
    manager.acquire("backup")
    manager.release("backup")
    assert not manager.is_locked("backup")


def test_release_noop_when_not_locked(manager: JobLockManager) -> None:
    # should not raise
    manager.release("nonexistent")


def test_current_lock_returns_none_when_unlocked(manager: JobLockManager) -> None:
    assert manager.current_lock("backup") is None


def test_current_lock_returns_info(manager: JobLockManager) -> None:
    manager.acquire("backup")
    info = manager.current_lock("backup")
    assert info is not None
    assert info.job_name == "backup"
    assert info.pid == os.getpid()


def test_lock_file_persists_on_disk(manager: JobLockManager, lock_dir: Path) -> None:
    manager.acquire("sync")
    lock_file = lock_dir / "sync.lock"
    assert lock_file.exists()
    content = lock_file.read_text()
    assert "sync" in content


def test_release_all_clears_multiple_locks(manager: JobLockManager) -> None:
    manager.acquire("job_a")
    manager.acquire("job_b")
    manager.release_all()
    assert not manager.is_locked("job_a")
    assert not manager.is_locked("job_b")


def test_lock_info_repr() -> None:
    info = LockInfo(job_name="test", pid=1234, acquired_at=time.time() - 5)
    r = repr(info)
    assert "test" in r
    assert "1234" in r


def test_job_name_with_spaces_safe(manager: JobLockManager, lock_dir: Path) -> None:
    manager.acquire("my job")
    lock_file = lock_dir / "my_job.lock"
    assert lock_file.exists()
    manager.release("my job")
    assert not lock_file.exists()
