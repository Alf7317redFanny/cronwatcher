"""Tests for cronwatcher.job_notifications."""
import json
import pytest
from pathlib import Path
from cronwatcher.job_notifications import NotificationPrefs, NotificationIndex


@pytest.fixture
def state_file(tmp_path: Path) -> str:
    return str(tmp_path / "notif.json")


@pytest.fixture
def index(state_file: str) -> NotificationIndex:
    return NotificationIndex(state_file=state_file)


def test_default_prefs_channels():
    prefs = NotificationPrefs()
    assert prefs.channels == ["log"]


def test_default_prefs_flags():
    prefs = NotificationPrefs()
    assert prefs.on_failure is True
    assert prefs.on_missed is True
    assert prefs.on_recovery is False


def test_invalid_channel_raises():
    with pytest.raises(ValueError, match="Unknown notification channel"):
        NotificationPrefs(channels=["sms"])


def test_valid_channels_accepted():
    prefs = NotificationPrefs(channels=["email", "webhook"])
    assert "email" in prefs.channels


def test_to_dict_roundtrip():
    prefs = NotificationPrefs(channels=["slack"], on_recovery=True)
    d = prefs.to_dict()
    restored = NotificationPrefs.from_dict(d)
    assert restored.channels == ["slack"]
    assert restored.on_recovery is True


def test_index_starts_empty(index: NotificationIndex):
    assert index.all() == {}


def test_get_missing_returns_defaults(index: NotificationIndex):
    prefs = index.get("nonexistent")
    assert prefs.channels == ["log"]
    assert prefs.on_failure is True


def test_set_and_get_roundtrip(index: NotificationIndex):
    prefs = NotificationPrefs(channels=["email"], on_recovery=True)
    index.set("backup", prefs)
    result = index.get("backup")
    assert result.channels == ["email"]
    assert result.on_recovery is True


def test_set_persists_to_disk(state_file: str):
    idx = NotificationIndex(state_file=state_file)
    idx.set("job1", NotificationPrefs(channels=["webhook"]))
    reloaded = NotificationIndex(state_file=state_file)
    assert reloaded.get("job1").channels == ["webhook"]


def test_remove_existing(index: NotificationIndex):
    index.set("job1", NotificationPrefs())
    assert index.remove("job1") is True
    assert index.get("job1").channels == ["log"]  # back to default


def test_remove_nonexistent_returns_false(index: NotificationIndex):
    assert index.remove("ghost") is False


def test_all_returns_all_jobs(index: NotificationIndex):
    index.set("a", NotificationPrefs(channels=["log"]))
    index.set("b", NotificationPrefs(channels=["email"]))
    assert set(index.all().keys()) == {"a", "b"}


def test_disk_file_is_valid_json(state_file: str):
    idx = NotificationIndex(state_file=state_file)
    idx.set("x", NotificationPrefs(channels=["slack"]))
    data = json.loads(Path(state_file).read_text())
    assert "x" in data
    assert data["x"]["channels"] == ["slack"]
