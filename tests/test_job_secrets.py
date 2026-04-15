"""Tests for cronwatcher.job_secrets."""
import pytest
from cronwatcher.job_secrets import SecretRef, SecretIndex


def test_secret_ref_valid():
    ref = SecretRef(key="MY_API_KEY", description="API key for service")
    assert ref.key == "MY_API_KEY"
    assert ref.description == "API key for service"


def test_secret_ref_strips_whitespace():
    ref = SecretRef(key="  DB_PASS  ")
    assert ref.key == "DB_PASS"


def test_secret_ref_empty_key_raises():
    with pytest.raises(ValueError, match="must not be empty"):
        SecretRef(key="")


def test_secret_ref_blank_key_raises():
    with pytest.raises(ValueError, match="must not be empty"):
        SecretRef(key="   ")


def test_secret_ref_repr():
    ref = SecretRef(key="TOKEN")
    assert "TOKEN" in repr(ref)


@pytest.fixture
def index():
    return SecretIndex()


def test_set_and_get_roundtrip(index):
    ref = SecretRef(key="vault:secret/db#password")
    index.set("backup-job", "DB_PASSWORD", ref)
    result = index.get("backup-job", "DB_PASSWORD")
    assert result is ref


def test_get_missing_returns_none(index):
    assert index.get("nonexistent", "SOME_VAR") is None


def test_get_missing_job_returns_none(index):
    index.set("job-a", "VAR", SecretRef(key="k"))
    assert index.get("job-b", "VAR") is None


def test_all_for_job_returns_all(index):
    index.set("job-a", "VAR1", SecretRef(key="k1"))
    index.set("job-a", "VAR2", SecretRef(key="k2"))
    result = index.all_for_job("job-a")
    assert set(result.keys()) == {"VAR1", "VAR2"}


def test_all_for_job_empty_if_none(index):
    assert index.all_for_job("ghost-job") == {}


def test_remove_existing_returns_true(index):
    index.set("job-a", "VAR", SecretRef(key="k"))
    assert index.remove("job-a", "VAR") is True
    assert index.get("job-a", "VAR") is None


def test_remove_missing_returns_false(index):
    assert index.remove("job-a", "NOPE") is False


def test_jobs_with_secret(index):
    index.set("job-a", "VAR", SecretRef(key="shared-key"))
    index.set("job-b", "VAR", SecretRef(key="shared-key"))
    index.set("job-c", "VAR", SecretRef(key="other-key"))
    result = index.jobs_with_secret("shared-key")
    assert set(result) == {"job-a", "job-b"}


def test_env_vars_for_job(index):
    index.set("job-a", "DB_PASS", SecretRef(key="k1"))
    index.set("job-a", "API_KEY", SecretRef(key="k2"))
    result = index.env_vars_for_job("job-a")
    assert set(result) == {"DB_PASS", "API_KEY"}


def test_env_vars_for_job_empty(index):
    assert index.env_vars_for_job("no-such-job") == []
