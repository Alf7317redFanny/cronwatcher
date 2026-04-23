"""Job lifecycle callbacks — run arbitrary callables on job events."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List

from cronwatcher.config import JobConfig

CallbackFn = Callable[[JobConfig, dict], None]


@dataclass
class CallbackEvent:
    """Represents a single callback invocation record."""
    job_name: str
    event: str  # 'on_start' | 'on_success' | 'on_failure'
    error: str | None = None

    def __repr__(self) -> str:
        status = f" error={self.error!r}" if self.error else ""
        return f"<CallbackEvent job={self.job_name!r} event={self.event!r}{status}>"


class CallbackRegistry:
    """Holds per-event callback lists and fires them during job lifecycle."""

    _VALID_EVENTS = ("on_start", "on_success", "on_failure")

    def __init__(self) -> None:
        self._hooks: Dict[str, List[CallbackFn]] = {
            e: [] for e in self._VALID_EVENTS
        }

    def register(self, event: str, fn: CallbackFn) -> None:
        if event not in self._VALID_EVENTS:
            raise ValueError(
                f"Unknown event {event!r}. Valid events: {self._VALID_EVENTS}"
            )
        self._hooks[event].append(fn)

    def fire(self, event: str, job: JobConfig, context: dict | None = None) -> list[CallbackEvent]:
        """Invoke all callbacks for *event*. Returns list of CallbackEvent results."""
        if event not in self._VALID_EVENTS:
            raise ValueError(f"Unknown event {event!r}")
        ctx = context or {}
        results: list[CallbackEvent] = []
        for fn in self._hooks[event]:
            record = CallbackEvent(job_name=job.name, event=event)
            try:
                fn(job, ctx)
            except Exception as exc:  # noqa: BLE001
                record.error = str(exc)
            results.append(record)
        return results

    def count(self, event: str) -> int:
        return len(self._hooks.get(event, []))

    def clear(self, event: str | None = None) -> None:
        if event is None:
            for e in self._VALID_EVENTS:
                self._hooks[e].clear()
        else:
            self._hooks[event].clear()
