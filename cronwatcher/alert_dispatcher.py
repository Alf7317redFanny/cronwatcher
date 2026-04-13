"""Dispatches alerts through plugins while respecting rate limits."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from cronwatcher.plugins import AlertPlugin
from cronwatcher.ratelimit import RateLimitConfig, RateLimiter

logger = logging.getLogger(__name__)


@dataclass
class DispatchResult:
    job_name: str
    sent: bool
    skipped_reason: Optional[str] = None
    plugin_errors: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"DispatchResult(job={self.job_name!r}, sent={self.sent}, "
            f"skipped={self.skipped_reason!r}, errors={self.plugin_errors})"
        )


class AlertDispatcher:
    """Sends alerts via registered plugins, gated by a RateLimiter."""

    def __init__(
        self,
        plugins: List[AlertPlugin],
        rate_limit_config: Optional[RateLimitConfig] = None,
    ) -> None:
        self._plugins = plugins
        self._limiter = RateLimiter(rate_limit_config or RateLimitConfig())

    def dispatch(self, job_name: str, subject: str, body: str) -> DispatchResult:
        if not self._limiter.is_allowed(job_name):
            logger.warning("Rate limit reached for job %r — alert suppressed", job_name)
            return DispatchResult(
                job_name=job_name,
                sent=False,
                skipped_reason="rate_limit_exceeded",
            )

        errors: List[str] = []
        for plugin in self._plugins:
            try:
                plugin.send(subject, body)
            except Exception as exc:  # noqa: BLE001
                logger.error("Plugin %r failed: %s", plugin.name, exc)
                errors.append(f"{plugin.name}: {exc}")

        self._limiter.record(job_name)
        return DispatchResult(
            job_name=job_name,
            sent=True,
            plugin_errors=errors,
        )

    def remaining_quota(self, job_name: str) -> int:
        return self._limiter.remaining(job_name)
