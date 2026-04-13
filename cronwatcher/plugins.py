"""Plugin interface for custom alert channels in cronwatcher."""

from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class AlertPlugin(ABC):
    """Base class for custom alert plugins."""

    @abstractmethod
    def send(self, subject: str, body: str) -> None:
        """Send an alert with the given subject and body."""
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__


class LogPlugin(AlertPlugin):
    """Built-in plugin that logs alerts to stdout."""

    def __init__(self, prefix: str = "[ALERT]"):
        self.prefix = prefix

    def send(self, subject: str, body: str) -> None:
        print(f"{self.prefix} {subject}\n{body}")


class PluginRegistry:
    """Manages registered alert plugins."""

    def __init__(self) -> None:
        self._plugins: List[AlertPlugin] = []

    def register(self, plugin: AlertPlugin) -> None:
        """Register an alert plugin instance."""
        if not isinstance(plugin, AlertPlugin):
            raise TypeError(f"Expected AlertPlugin, got {type(plugin).__name__}")
        self._plugins.append(plugin)

    def dispatch(self, subject: str, body: str) -> None:
        """Send an alert through all registered plugins."""
        for plugin in self._plugins:
            try:
                plugin.send(subject, body)
            except Exception as exc:  # noqa: BLE001
                print(f"[cronwatcher] Plugin {plugin.name!r} failed: {exc}")

    def load_from_config(self, plugin_configs: List[Dict[str, Any]]) -> None:
        """Dynamically load plugins from config dicts with 'module' and 'class' keys."""
        for cfg in plugin_configs:
            module_path = cfg["module"]
            class_name = cfg["class"]
            kwargs = cfg.get("kwargs", {})
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            self.register(cls(**kwargs))

    @property
    def plugins(self) -> List[AlertPlugin]:
        return list(self._plugins)

    def clear(self) -> None:
        self._plugins.clear()
