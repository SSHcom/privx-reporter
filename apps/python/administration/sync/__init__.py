import argparse
from typing import Any

from administration.sync.backfill.module import handle_backfill
from administration.sync.trend.module import handle_trend_sync


def handle(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, str | None]:
    """Route sync administration actions to the requested subcommand."""
    subcommand = args.subcommand

    if subcommand == "backfill":
        return handle_backfill(args, config)

    if subcommand == "trend":
        return handle_trend_sync(args, config)

    return {"error_message": f"Invalid sync subcommand '{subcommand}'", "info_message": None}


__all__ = ["handle"]
