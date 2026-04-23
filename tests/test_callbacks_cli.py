"""Tests for cronwatcher.callbacks_cli."""
import argparse
import io

import pytest

from cronwatcher.callbacks_cli import add_callbacks_args, callbacks_summary, run_callbacks_cmd
from cronwatcher.job_callbacks import CallbackRegistry


@pytest.fixture
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command")
    add_callbacks_args(sub)
    return p


@pytest.fixture
def registry() -> CallbackRegistry:
    return CallbackRegistry()


def _args(parser: argparse.ArgumentParser, argv: list[str]) -> argparse.Namespace:
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Parser registration
# ---------------------------------------------------------------------------

def test_add_callbacks_args_registers_subcommand(parser):
    ns = _args(parser, ["callbacks"])
    assert ns.command == "callbacks"


def test_default_event_is_none(parser):
    ns = _args(parser, ["callbacks"])
    assert ns.event is None


def test_event_flag_accepted(parser):
    ns = _args(parser, ["callbacks", "--event", "on_success"])
    assert ns.event == "on_success"


def test_invalid_event_raises(parser):
    with pytest.raises(SystemExit):
        _args(parser, ["callbacks", "--event", "on_timeout"])


# ---------------------------------------------------------------------------
# run_callbacks_cmd
# ---------------------------------------------------------------------------

def test_empty_registry_prints_zeros(parser, registry):
    ns = _args(parser, ["callbacks"])
    out = io.StringIO()
    rc = run_callbacks_cmd(ns, registry, out=out)
    assert rc == 0
    text = out.getvalue()
    assert "on_start: 0" in text
    assert "on_success: 0" in text
    assert "on_failure: 0" in text


def test_counts_reflect_registered_callbacks(parser, registry):
    registry.register("on_success", lambda j, c: None)
    registry.register("on_success", lambda j, c: None)
    ns = _args(parser, ["callbacks"])
    out = io.StringIO()
    run_callbacks_cmd(ns, registry, out=out)
    assert "on_success: 2" in out.getvalue()


def test_event_filter_shows_only_requested_event(parser, registry):
    registry.register("on_start", lambda j, c: None)
    ns = _args(parser, ["callbacks", "--event", "on_start"])
    out = io.StringIO()
    run_callbacks_cmd(ns, registry, out=out)
    text = out.getvalue()
    assert "on_start" in text
    assert "on_success" not in text


def test_total_line_present(parser, registry):
    registry.register("on_failure", lambda j, c: None)
    ns = _args(parser, ["callbacks"])
    out = io.StringIO()
    run_callbacks_cmd(ns, registry, out=out)
    assert "Total: 1" in out.getvalue()


# ---------------------------------------------------------------------------
# callbacks_summary
# ---------------------------------------------------------------------------

def test_callbacks_summary_format(registry):
    summary = callbacks_summary(registry)
    assert summary.startswith("callbacks(")
    assert "on_start=0" in summary
    assert "on_success=0" in summary
    assert "on_failure=0" in summary


def test_callbacks_summary_reflects_counts(registry):
    registry.register("on_failure", lambda j, c: None)
    summary = callbacks_summary(registry)
    assert "on_failure=1" in summary
