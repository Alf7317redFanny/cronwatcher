"""Webhook alert plugin for cronwatcher."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WebhookConfig:
    url: str
    method: str = "POST"
    headers: dict = field(default_factory=lambda: {"Content-Type": "application/json"})
    timeout: int = 10
    secret: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.url:
            raise ValueError("Webhook URL must not be empty")
        if self.method not in ("POST", "PUT"):
            raise ValueError(f"Unsupported HTTP method: {self.method}")
        if self.timeout <= 0:
            raise ValueError("Timeout must be a positive integer")


@dataclass
class WebhookPayload:
    job_name: str
    event: str
    message: str
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "event": self.event,
            "message": self.message,
            "timestamp": self.timestamp,
        }


class WebhookSender:
    def __init__(self, config: WebhookConfig) -> None:
        self.config = config

    def send(self, payload: WebhookPayload) -> bool:
        """Send a webhook notification. Returns True on success."""
        data = json.dumps(payload.to_dict()).encode("utf-8")
        headers = dict(self.config.headers)
        if self.config.secret:
            headers["X-Webhook-Secret"] = self.config.secret

        req = urllib.request.Request(
            self.config.url,
            data=data,
            headers=headers,
            method=self.config.method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                return 200 <= resp.status < 300
        except urllib.error.URLError:
            return False
        except Exception:
            return False
