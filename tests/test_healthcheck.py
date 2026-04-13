"""Tests for cronwatcher.healthcheck."""

from __future__ import annotations

import json
import socket
import time
from urllib import request as urllib_request
from urllib.error import HTTPError

import pytest

from cronwatcher.healthcheck import HealthStatus, HealthcheckServer


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _free_port() -> int:
    """Return an ephemeral port that is currently unused."""
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _get(url: str) -> tuple[int, dict]:
    try:
        with urllib_request.urlopen(url, timeout=3) as resp:
            return resp.status, json.loads(resp.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


# ---------------------------------------------------------------------------
# HealthStatus unit tests
# ---------------------------------------------------------------------------

class TestHealthStatus:
    def test_to_dict_keys(self):
        s = HealthStatus("backup", True, "2024-01-01T00:00:00", 0)
        d = s.to_dict()
        assert set(d.keys()) == {"job", "healthy", "last_run", "last_exit_code"}

    def test_to_dict_values(self):
        s = HealthStatus("sync", False, None, 1)
        d = s.to_dict()
        assert d["job"] == "sync"
        assert d["healthy"] is False
        assert d["last_run"] is None
        assert d["last_exit_code"] == 1


# ---------------------------------------------------------------------------
# HealthcheckServer integration tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def healthy_server():
    port = _free_port()
    statuses = [
        HealthStatus("job_a", True, "2024-06-01T10:00:00", 0),
        HealthStatus("job_b", True, "2024-06-01T11:00:00", 0),
    ]
    srv = HealthcheckServer("127.0.0.1", port, lambda: statuses)
    srv.start()
    time.sleep(0.05)  # give the thread a moment
    yield srv, port
    srv.stop()


@pytest.fixture()
def unhealthy_server():
    port = _free_port()
    statuses = [
        HealthStatus("job_a", True, "2024-06-01T10:00:00", 0),
        HealthStatus("job_b", False, "2024-06-01T09:00:00", 1),
    ]
    srv = HealthcheckServer("127.0.0.1", port, lambda: statuses)
    srv.start()
    time.sleep(0.05)
    yield srv, port
    srv.stop()


def test_health_returns_200_when_all_ok(healthy_server):
    _, port = healthy_server
    status, body = _get(f"http://127.0.0.1:{port}/health")
    assert status == 200
    assert body["ok"] is True


def test_health_lists_all_jobs(healthy_server):
    _, port = healthy_server
    _, body = _get(f"http://127.0.0.1:{port}/health")
    assert len(body["jobs"]) == 2


def test_health_returns_503_when_any_unhealthy(unhealthy_server):
    _, port = unhealthy_server
    status, body = _get(f"http://127.0.0.1:{port}/health")
    assert status == 503
    assert body["ok"] is False


def test_unknown_path_returns_404(healthy_server):
    _, port = healthy_server
    status, _ = _get(f"http://127.0.0.1:{port}/unknown")
    assert status == 404
