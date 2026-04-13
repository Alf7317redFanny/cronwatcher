"""Tests for cronwatcher.webhook_registry module."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from cronwatcher.webhook import WebhookConfig, WebhookPayload
from cronwatcher.webhook_registry import WebhookRegistry


@pytest.fixture
def payload() -> WebhookPayload:
    return WebhookPayload(
        job_name="sync",
        event="missed",
        message="Job sync missed its scheduled run",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def registry() -> WebhookRegistry:
    reg = WebhookRegistry()
    reg.register(WebhookConfig(url="https://a.example.com/hook"))
    reg.register(WebhookConfig(url="https://b.example.com/hook"))
    return reg


def _mock_resp(status: int) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_registry_count(registry: WebhookRegistry) -> None:
    assert registry.count == 2


def test_broadcast_all_success(registry: WebhookRegistry, payload: WebhookPayload) -> None:
    with patch("urllib.request.urlopen", return_value=_mock_resp(200)):
        results = registry.broadcast(payload)
    assert results == [True, True]


def test_broadcast_all_ok_true(registry: WebhookRegistry, payload: WebhookPayload) -> None:
    with patch("urllib.request.urlopen", return_value=_mock_resp(200)):
        assert registry.broadcast_all_ok(payload) is True


def test_broadcast_partial_failure(registry: WebhookRegistry, payload: WebhookPayload) -> None:
    import urllib.error
    responses = [_mock_resp(200), urllib.error.URLError("timeout")]

    def side_effect(*args, **kwargs):
        val = responses.pop(0)
        if isinstance(val, Exception):
            raise val
        return val

    with patch("urllib.request.urlopen", side_effect=side_effect):
        assert registry.broadcast_all_ok(payload) is False


def test_empty_registry_broadcast_all_ok(payload: WebhookPayload) -> None:
    reg = WebhookRegistry()
    assert reg.broadcast_all_ok(payload) is False


def test_from_dicts_builds_registry() -> None:
    raw = [
        {"url": "https://x.example.com", "secret": "tok"},
        {"url": "https://y.example.com", "method": "PUT", "timeout": 5},
    ]
    reg = WebhookRegistry.from_dicts(raw)
    assert reg.count == 2


def test_register_many() -> None:
    configs = [
        WebhookConfig(url="https://c.example.com"),
        WebhookConfig(url="https://d.example.com"),
    ]
    reg = WebhookRegistry()
    reg.register_many(configs)
    assert reg.count == 2
