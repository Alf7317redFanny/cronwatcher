"""Registry that manages multiple webhook endpoints and dispatches alerts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronwatcher.webhook import WebhookConfig, WebhookPayload, WebhookSender


@dataclass
class WebhookRegistry:
    """Holds multiple WebhookSender instances and broadcasts payloads."""

    _senders: List[WebhookSender] = field(default_factory=list, init=False, repr=False)

    def register(self, config: WebhookConfig) -> None:
        """Register a new webhook endpoint."""
        self._senders.append(WebhookSender(config))

    def register_many(self, configs: List[WebhookConfig]) -> None:
        for cfg in configs:
            self.register(cfg)

    def broadcast(self, payload: WebhookPayload) -> List[bool]:
        """Send payload to all registered webhooks. Returns per-sender results."""
        return [sender.send(payload) for sender in self._senders]

    def broadcast_all_ok(self, payload: WebhookPayload) -> bool:
        """Returns True only if every registered webhook succeeded."""
        results = self.broadcast(payload)
        return bool(results) and all(results)

    @property
    def count(self) -> int:
        return len(self._senders)

    @classmethod
    def from_dicts(cls, raw: List[dict]) -> "WebhookRegistry":
        """Build a registry from a list of raw config dicts."""
        registry = cls()
        for item in raw:
            cfg = WebhookConfig(
                url=item["url"],
                method=item.get("method", "POST"),
                headers=item.get("headers", {"Content-Type": "application/json"}),
                timeout=item.get("timeout", 10),
                secret=item.get("secret"),
            )
            registry.register(cfg)
        return registry
