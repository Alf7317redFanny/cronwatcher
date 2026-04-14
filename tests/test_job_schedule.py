"""Tests for cronwatcher.job_schedule."""
import pytest
from datetime import datetime

from cronwatcher.job_schedule import (
    normalize,
    is_valid,
    describe,
    schedule_info,
    ScheduleInfo,
)


# ---------------------------------------------------------------------------
# normalize
# ---------------------------------------------------------------------------

def test_normalize_preset_hourly():
    assert normalize("@hourly") == "0 * * * *"


def test_normalize_preset_daily():
    assert normalize("@daily") == "0 0 * * *"


def test_normalize_midnight_alias():
    assert normalize("@midnight") == "0 0 * * *"


def test_normalize_passthrough_for_standard_expression():
    expr = "*/5 * * * *"
    assert normalize(expr) == expr


def test_normalize_strips_whitespace():
    assert normalize("  @weekly  ") == "0 0 * * 0"


# ---------------------------------------------------------------------------
# is_valid
# ---------------------------------------------------------------------------

def test_is_valid_standard_expression():
    assert is_valid("0 12 * * 1") is True


def test_is_valid_preset():
    assert is_valid("@monthly") is True


def test_is_valid_rejects_garbage():
    assert is_valid("not-a-cron") is False


def test_is_valid_rejects_too_few_fields():
    assert is_valid("* * *") is False


# ---------------------------------------------------------------------------
# describe
# ---------------------------------------------------------------------------

def test_describe_every_minute():
    assert describe("* * * * *") == "every minute"


def test_describe_preset_includes_alias():
    result = describe("@daily")
    assert "@daily" in result
    assert "0 0 * * *" in result


def test_describe_specific_fields():
    result = describe("30 6 * * 1")
    assert "minute=30" in result
    assert "hour=6" in result
    assert "day-of-week=1" in result


# ---------------------------------------------------------------------------
# schedule_info
# ---------------------------------------------------------------------------

@pytest.fixture
def base_time() -> datetime:
    return datetime(2024, 6, 15, 12, 0, 0)


def test_schedule_info_returns_schedule_info_instance(base_time):
    info = schedule_info("0 * * * *", base=base_time)
    assert isinstance(info, ScheduleInfo)


def test_schedule_info_next_run_after_base(base_time):
    info = schedule_info("0 * * * *", base=base_time)
    assert info.next_run > base_time


def test_schedule_info_prev_run_before_base(base_time):
    info = schedule_info("0 * * * *", base=base_time)
    assert info.prev_run <= base_time


def test_schedule_info_normalized_stored(base_time):
    info = schedule_info("@hourly", base=base_time)
    assert info.normalized == "0 * * * *"


def test_schedule_info_invalid_expression_raises():
    with pytest.raises(ValueError, match="Invalid cron expression"):
        schedule_info("bad expr")


def test_schedule_info_description_populated(base_time):
    info = schedule_info("0 9 * * *", base=base_time)
    assert info.description != ""
