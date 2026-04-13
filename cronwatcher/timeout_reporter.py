"""Format and report timeout violations via the alert dispatcher."""
from __future__ import annotations

from typing import List

from cronwatcher.alert_dispatcher import AlertDispatcher, DispatchResult
from cronwatcher.job_timeout import TimeoutViolation


DEFAULT_SUBJECT_TEMPLATE = "[cronwatcher] Timeout: {job_name} ran for {actual:.1f}s (limit {limit}s)"
DEFAULT_BODY_TEMPLATE = (
    "Job '{job_name}' exceeded its configured timeout.\n"
    "Allowed : {limit} seconds\n"
    "Actual  : {actual:.1f} seconds\n"
    "Excess  : {excess:.1f} seconds\n"
)


def _format_subject(violation: TimeoutViolation, template: str) -> str:
    return template.format(
        job_name=violation.job_name,
        actual=violation.actual_seconds,
        limit=violation.allowed_seconds,
    )


def _format_body(violation: TimeoutViolation, template: str) -> str:
    excess = violation.actual_seconds - violation.allowed_seconds
    return template.format(
        job_name=violation.job_name,
        actual=violation.actual_seconds,
        limit=violation.allowed_seconds,
        excess=excess,
    )


class TimeoutReporter:
    """Sends alert dispatches for :class:`TimeoutViolation` instances."""

    def __init__(
        self,
        dispatcher: AlertDispatcher,
        subject_template: str = DEFAULT_SUBJECT_TEMPLATE,
        body_template: str = DEFAULT_BODY_TEMPLATE,
    ) -> None:
        self._dispatcher = dispatcher
        self._subject_tpl = subject_template
        self._body_tpl = body_template

    def report(self, violation: TimeoutViolation) -> DispatchResult:
        """Dispatch a single timeout alert and return the result."""
        subject = _format_subject(violation, self._subject_tpl)
        body = _format_body(violation, self._body_tpl)
        return self._dispatcher.dispatch(subject=subject, body=body)

    def report_many(self, violations: List[TimeoutViolation]) -> List[DispatchResult]:
        """Dispatch alerts for every violation; returns one result per item."""
        return [self.report(v) for v in violations]
