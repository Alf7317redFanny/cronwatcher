"""Healthcheck endpoint support for cronwatcher — exposes a simple HTTP
server that reports the current status of all monitored jobs so external
uptime monitors (e.g. UptimeRobot, Pingdom) can poll it."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable


@dataclass
class HealthStatus:
    job_name: str
    healthy: bool
    last_run: str | None
    last_exit_code: int | None

    def to_dict(self) -> dict:
        return {
            "job": self.job_name,
            "healthy": self.healthy,
            "last_run": self.last_run,
            "last_exit_code": self.last_exit_code,
        }


class HealthcheckServer:
    """Runs a lightweight HTTP server in a daemon thread.

    GET /health  — returns JSON with per-job status + overall ok flag.
    """

    def __init__(self, host: str, port: int, status_fn: Callable[[], list[HealthStatus]]):
        self.host = host
        self.port = port
        self._status_fn = status_fn
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    def _make_handler(self):
        status_fn = self._status_fn

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != "/health":
                    self.send_response(404)
                    self.end_headers()
                    return

                statuses = status_fn()
                overall_ok = all(s.healthy for s in statuses)
                body = json.dumps(
                    {
                        "ok": overall_ok,
                        "jobs": [s.to_dict() for s in statuses],
                    }
                ).encode()

                self.send_response(200 if overall_ok else 503)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):  # silence default stderr logging
                pass

        return _Handler

    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the HTTP server in a background daemon thread."""
        self._server = HTTPServer((self.host, self.port), self._make_handler())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Shut the server down gracefully."""
        if self._server:
            self._server.shutdown()
