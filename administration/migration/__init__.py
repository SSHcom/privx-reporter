import argparse
from typing import Any

from administration.migration.down.module import handle_down_migration
from administration.migration.status.module import handle_status_migration
from administration.migration.up.module import handle_up_migration


def apply() -> dict[str, str | None]:
    """Apply all pending migrations."""
    return handle_up_migration()


def handle(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, str | None]:
    """Route migration administration actions to the requested subcommand."""
    _ = config
    subcommand = args.subcommand

    if subcommand == "up":
        return handle_up_migration()

    if subcommand == "down":
        return handle_down_migration(args)

    if subcommand == "status":
        return handle_status_migration()

    return {"error_message": f"Invalid migration subcommand '{subcommand}'", "info_message": None}


__all__ = ["handle", "apply"]
