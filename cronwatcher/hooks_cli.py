"""CLI helpers for listing registered hooks (debug/info use)."""
from cronwatcher.job_runner_hooks import HookRegistry


def hooks_summary(registry: HookRegistry) -> str:
    """Return a human-readable summary of registered hooks."""
    lines = [
        f"Pre-run hooks : {len(registry._pre)}",
        f"Post-run hooks: {len(registry._post)}",
        f"Failure hooks : {len(registry._failure)}",
    ]
    return "\n".join(lines)


def add_hooks_args(parser) -> None:
    """Add hook-related flags to an argparse parser."""
    parser.add_argument(
        "--list-hooks",
        action="store_true",
        default=False,
        help="Print registered hook counts and exit.",
    )


def run_hooks_cmd(args, registry: HookRegistry) -> bool:
    """Handle --list-hooks flag. Returns True if handled."""
    if getattr(args, "list_hooks", False):
        print(hooks_summary(registry))
        return True
    return False
