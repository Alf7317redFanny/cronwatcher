"""Utilities for parsing and describing cron schedules in human-readable form."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from croniter import croniter
from datetime import datetime


_PRESETS: dict[str, str] = {
    "@hourly": "0 * * * *",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@weekly": "0 0 * * 0",
    "@monthly": "0 0 1 * *",
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
}

_FIELD_NAMES = ["minute", "hour", "day-of-month", "month", "day-of-week"]


@dataclass
class ScheduleInfo:
    expression: str
    normalized: str
    description: str
    next_run: datetime
    prev_run: datetime

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ScheduleInfo(expr={self.expression!r}, "
            f"next={self.next_run.isoformat()}, prev={self.prev_run.isoformat()})"
        )


def normalize(expression: str) -> str:
    """Expand preset aliases to five-field cron expressions."""
    return _PRESETS.get(expression.strip().lower(), expression.strip())


def is_valid(expression: str) -> bool:
    """Return True if *expression* is a valid cron expression (or known preset)."""
    try:
        croniter(normalize(expression))
        return True
    except (ValueError, KeyError):
        return False


def describe(expression: str) -> str:
    """Return a short human-readable description of the schedule."""
    norm = normalize(expression)
    if norm != expression.strip():
        return f"preset '{expression.strip()}' ({norm})"
    parts = norm.split()
    if len(parts) != 5:
        return norm
    labels = [f"{_FIELD_NAMES[i]}={parts[i]}" for i in range(5) if parts[i] != "*"]
    return ", ".join(labels) if labels else "every minute"


def schedule_info(expression: str, base: Optional[datetime] = None) -> ScheduleInfo:
    """Return a :class:`ScheduleInfo` for the given cron expression."""
    if not is_valid(expression):
        raise ValueError(f"Invalid cron expression: {expression!r}")
    norm = normalize(expression)
    base = base or datetime.utcnow()
    cron = croniter(norm, base)
    next_run: datetime = cron.get_next(datetime)
    cron2 = croniter(norm, base)
    prev_run: datetime = cron2.get_prev(datetime)
    return ScheduleInfo(
        expression=expression,
        normalized=norm,
        description=describe(expression),
        next_run=next_run,
        prev_run=prev_run,
    )
