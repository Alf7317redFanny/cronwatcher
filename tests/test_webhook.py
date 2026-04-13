"""Tests for cronwatcher.webhook module."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.webhook import WebhookConfig, WebhookPayload, WebhookSender


@pytest.fixture
def config() -> WebhookConfig:
    return WebhookConfig(url="https://example.com/hook")


@pytest.fixture
def payload() -> WebhookPayload:
    return WebhookPayload(
        job_name="backup",
        event="failure",
        message="Job backup failed with exit code 1",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def sender(config: WebhookConfig) -> WebhookSender:
    return WebhookSender(config)


def test_config_valid(config: WebhookConfig) -> None:
    assert config.url == "https://example.com/hook"
    assert config.method == "POST"
    assert config.timeout == 10


def test_config_empty_url_raises() -> None:
    with pytest.raises(ValueError, match="URL"):
        WebhookConfig(url="")


def test_config_invalid_method_raises() -> None:
    with pytest.raises(ValueError, match="method"):
        WebhookConfig(url="https://example.com", method="GET")


def test_config_invalid_timeout_raises() -> None:
    with pytest.raises(ValueError, match="Timeout"):
        WebhookConfig(url="https://example.com", timeout=0)


def test_payload_to_dict(payload: WebhookPayload) -> None:
    d = payload.to_dict()
    assert d["job_name"] == "backup"
    assert d["event"] == "failure"
    assert "message" in d
    assert "timestamp" in d


def test_send_success(sender: WebhookSender, payload: WebhookPayload) -> None:
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = sender.send(payload)

    assert result is True


def test_send_failure_on_url_error(sender: WebhookSender, payload: WebhookPayload) -> None:
    import urllib.error

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        result = sender.send(payload)

    assert result is False


def test_send_includes_secret(payload: WebhookPayload) -> None:
    cfg = WebhookConfig(url="https://example.com/hook", secret="mysecret")
    sender = WebhookSender(cfg)

    captured = {}

    def fake_urlopen(req, timeout):
        captured["headers"] = dict(req.headers)
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        sender.send(payload)

    assert "X-webhook-secret" in captured["headers"]
