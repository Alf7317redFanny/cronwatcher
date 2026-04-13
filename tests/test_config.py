"""Tests for cronwatcher config loading."""

import json
import pytest
import tempfile
import os

from cronwatcher.config import JobConfig, WatcherConfig


def write_temp_config(data: dict) -> str:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, tmp)
    tmp.close()
    return tmp.name


class TestJobConfig:
    def test_valid_job(self):
        job = JobConfig(name="test-job", schedule="* * * * *")
        assert job.name == "test-job"
        assert job.timeout == 300
        assert job.tags == []

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name cannot be empty"):
            JobConfig(name="", schedule="* * * * *")

    def test_empty_schedule_raises(self):
        with pytest.raises(ValueError, match="schedule cannot be empty"):
            JobConfig(name="job", schedule="")

    def test_invalid_timeout_raises(self):
        with pytest.raises(ValueError, match="Timeout must be a positive integer"):
            JobConfig(name="job", schedule="* * * * *", timeout=-1)


class TestWatcherConfig:
    def test_from_dict_basic(self):
        data = {
            "jobs": [
                {"name": "sync", "schedule": "0 * * * *"}
            ]
        }
        config = WatcherConfig.from_dict(data)
        assert len(config.jobs) == 1
        assert config.jobs[0].name == "sync"
        assert config.log_file == "/var/log/cronwatcher.log"

    def test_from_dict_overrides_defaults(self):
        data = {
            "log_file": "/tmp/test.log",
            "default_alert_email": "admin@test.com",
            "jobs": []
        }
        config = WatcherConfig.from_dict(data)
        assert config.log_file == "/tmp/test.log"
        assert config.default_alert_email == "admin@test.com"

    def test_load_from_file(self):
        data = {
            "jobs": [
                {"name": "backup", "schedule": "0 2 * * *", "timeout": 600, "tags": ["critical"]}
            ]
        }
        path = write_temp_config(data)
        try:
            config = WatcherConfig.load(path)
            assert config.jobs[0].timeout == 600
            assert "critical" in config.jobs[0].tags
        finally:
            os.unlink(path)

    def test_load_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            WatcherConfig.load("/nonexistent/path/config.json")
