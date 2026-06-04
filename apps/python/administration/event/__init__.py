import argparse
from typing import Any

from administration.event.disable.module import handle_disable_event
from administration.event.enable.module import handle_enable_event
from administration.event.list.module import handle_list_event


def handle(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, str | None]:
    """Route event administration actions to the requested subcommand."""
    subcommand = args.subcommand

    if subcommand == "enable":
        return handle_enable_event(args, config)

    if subcommand == "disable":
        return handle_disable_event(args, config)

    if subcommand == "list":
        return handle_list_event(args, config)

    return {"error_message": f"Invalid event subcommand '{subcommand}'", "info_message": None}


__all__ = ["handle"]
