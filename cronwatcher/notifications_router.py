"""Routes alerts to the correct channels based on per-job notification prefs."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
from cronwatcher.job_notifications import NotificationIndex, NotificationPrefs
from cronwatcher.alert_dispatcher import AlertDispatcher, DispatchResult


@dataclass
class RoutedAlert:
    job_name: str
    event: str  # 'failure' | 'missed' | 'recovery'
    message: str
    channels_used: List[str]
    results: List[DispatchResult]

    def __repr__(self) -> str:
        ok = all(not r.errors for r in self.results)
        return (
            f"RoutedAlert(job={self.job_name!r}, event={self.event!r}, "
            f"channels={self.channels_used}, ok={ok})"
        )


class NotificationsRouter:
    """Decides which channels receive an alert based on NotificationPrefs."""

    def __init__(
        self,
        index: NotificationIndex,
        dispatcher: AlertDispatcher,
    ) -> None:
        self._index = index
        self._dispatcher = dispatcher

    def route(self, job_name: str, event: str, message: str) -> RoutedAlert:
        """Route *message* for *job_name* / *event* to configured channels.

        *event* must be one of 'failure', 'missed', or 'recovery'.
        """
        if event not in ("failure", "missed", "recovery"):
            raise ValueError(f"Unknown event type: {event!r}")

        prefs: NotificationPrefs = self._index.get(job_name)

        should_send = {
            "failure": prefs.on_failure,
            "missed": prefs.on_missed,
            "recovery": prefs.on_recovery,
        }[event]

        if not should_send:
            return RoutedAlert(
                job_name=job_name,
                event=event,
                message=message,
                channels_used=[],
                results=[],
            )

        results: List[DispatchResult] = []
        for channel in prefs.channels:
            result = self._dispatcher.dispatch(
                subject=f"[cronwatcher] {event.upper()}: {job_name}",
                body=message,
                channel=channel,
            )
            results.append(result)

        return RoutedAlert(
            job_name=job_name,
            event=event,
            message=message,
            channels_used=list(prefs.channels),
            results=results,
        )
