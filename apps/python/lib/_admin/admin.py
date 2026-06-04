# Tests are not necessary for this module.

import argparse
import importlib
import logging
from typing import Any, Protocol, cast


class AdminCommandHandler(Protocol):
    """Protocol for admin command group handlers."""

    def handle(self, args: argparse.Namespace, config: dict[str, Any]) -> dict[str, str | None]: ...


logger = logging.getLogger(__name__)


def run(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, str | None]:
    """Route to the appropriate admin command handler."""
    command = args.command

    try:
        module_name = f"administration.{command}"
        module = importlib.import_module(module_name)
        handler = cast("AdminCommandHandler", module)
        return handler.handle(args, config)
    except (ImportError, AttributeError):
        return {"error_message": f"Invalid admin command '{command}'", "info_message": None}
    except SystemExit:
        raise
    except Exception as e:
        logger.exception("Unexpected admin error")
        return {"error_message": f"Unexpected admin error: {e}", "info_message": None}
