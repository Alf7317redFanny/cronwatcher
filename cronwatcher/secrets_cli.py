"""CLI helpers for managing job secret references."""
from __future__ import annotations

import argparse
from typing import List

from cronwatcher.job_secrets import SecretIndex, SecretRef


def add_secrets_args(parser: argparse.ArgumentParser) -> None:
    """Add --secret flags to an argument parser.

    Format: --secret ENV_VAR=secret-key[:description]
    Example: --secret DB_PASS=vault:db/prod#password
    """
    parser.add_argument(
        "--secret",
        dest="secrets",
        metavar="VAR=KEY",
        action="append",
        default=[],
        help="Attach a secret reference to an env var (VAR=secret-key).",
    )


def parse_secret_args(raw: List[str]) -> List[tuple[str, SecretRef]]:
    """Parse a list of 'VAR=key' strings into (env_var, SecretRef) pairs.

    Raises ValueError on malformed entries.
    """
    results = []
    for entry in raw:
        if "=" not in entry:
            raise ValueError(
                f"Invalid secret spec {entry!r}: expected VAR=key format"
            )
        env_var, _, key = entry.partition("=")
        env_var = env_var.strip()
        key = key.strip()
        if not env_var:
            raise ValueError(f"Empty env var name in secret spec {entry!r}")
        results.append((env_var, SecretRef(key=key)))
    return results


def apply_secrets_to_index(
    job_name: str,
    raw: List[str],
    index: SecretIndex,
) -> int:
    """Parse raw secret specs and register them in the index.

    Returns the number of secrets applied.
    """
    pairs = parse_secret_args(raw)
    for env_var, ref in pairs:
        index.set(job_name, env_var, ref)
    return len(pairs)


def secrets_summary(job_name: str, index: SecretIndex) -> str:
    """Return a human-readable summary of secrets attached to a job."""
    refs = index.all_for_job(job_name)
    if not refs:
        return f"{job_name}: no secrets configured"
    lines = [f"{job_name} secrets:"]
    for env_var, ref in sorted(refs.items()):
        desc = f" ({ref.description})" if ref.description else ""
        lines.append(f"  {env_var} -> {ref.key}{desc}")
    return "\n".join(lines)
