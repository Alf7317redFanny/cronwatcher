"""CLI helpers for job environment variable management."""
from __future__ import annotations

import argparse
from typing import List

from cronwatcher.job_env import EnvIndex


def add_env_args(parser: argparse.ArgumentParser) -> None:
    """Attach --env flags to an argument parser."""
    parser.add_argument(
        "--env",
        metavar="KEY=VALUE",
        action="append",
        dest="env_overrides",
        default=[],
        help="Set an environment variable for this job (repeatable).",
    )


def parse_env_overrides(raw: List[str]) -> dict:
    """Parse a list of 'KEY=VALUE' strings into a dict."""
    result = {}
    for item in raw:
        if "=" not in item:
            raise argparse.ArgumentTypeError(
                f"Invalid --env format {item!r}: expected KEY=VALUE"
            )
        key, _, value = item.partition("=")
        key = key.strip()
        if not key:
            raise argparse.ArgumentTypeError(
                f"Invalid --env format {item!r}: key must not be empty"
            )
        result[key] = value
    return result


def apply_env_to_index(index: EnvIndex, job_name: str, raw: List[str]) -> None:
    """Parse raw KEY=VALUE strings and store them in the index."""
    for key, value in parse_env_overrides(raw).items():
        index.set(job_name, key, value)


def env_summary(index: EnvIndex, job_name: str) -> str:
    """Return a human-readable summary of env vars for a job."""
    env = index.all_for_job(job_name)
    if not env:
        return f"{job_name}: (no env overrides)"
    lines = [f"{job_name} env overrides:"]
    for k, v in sorted(env.items()):
        lines.append(f"  {k}={v}")
    return "\n".join(lines)
