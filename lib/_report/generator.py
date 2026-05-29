# Tests are not necessary for this module.

import argparse
import importlib
import logging
from dataclasses import dataclass
from typing import Any, Protocol, cast

import privx_api

from lib._report.error import ReportError, handle_error


class ReportGroupHandler(Protocol):
    """Protocol for report group handler modules."""

    # Needed to satisfy type checker
    def handle(
        self,
        api: privx_api.PrivXAPI,
        args: argparse.Namespace,
        config: dict[str, Any],
        user_group_id: str | None = None,
    ) -> dict[str, Any]: ...


class ReportListHandler(Protocol):
    """Protocol for report group modules that support UI list retrieval."""

    def get_list(self, subcommand: str, list_key: str) -> "UIListResponse": ...


@dataclass
class UIListResponse:
    """Response shape for UI list retrieval."""

    values: list[str]
    error_message: str | None = None


logger = logging.getLogger(__name__)


def get_list(command: str, subcommand: str, list_key: str) -> UIListResponse:
    """Retrieve UI list values for a command, subcommand, and list key.

    Args:
        command: The report command (e.g., "events")
        subcommand: The report subcommand (e.g., "query")
        list_key: The list key to retrieve (e.g., "event_names")

    Returns:
        UIListResponse with values or error_message
    """
    try:
        module_name = f"reports.{command}"
        module = importlib.import_module(module_name)

        if not hasattr(module, "get_list"):
            return UIListResponse(
                values=[],
                error_message=f"Report type '{command}' does not support UI lists",
            )

        handler = cast("ReportListHandler", module)
        return handler.get_list(subcommand, list_key)

    except ImportError:
        return UIListResponse(
            values=[],
            error_message=f"Invalid report type '{command}'",
        )
    except Exception as e:
        return UIListResponse(
            values=[],
            error_message=f"Error retrieving list: {str(e)}",
        )


def generate(
    api: privx_api.PrivXAPI,
    args: argparse.Namespace,
    config: dict[str, Any],
    user_group_id: str | None = None,
) -> dict[str, Any]:
    """Route to appropriate handler based on the command."""
    command = args.command

    if user_group_id:
        logger.info(f"Generating report for UI user in group: {user_group_id}")

    try:
        module_name = f"reports.{command}"
        module = importlib.import_module(module_name)
        handler = cast("ReportGroupHandler", module)
        return handler.handle(api, args, config, user_group_id=user_group_id)
    except (ImportError, AttributeError):
        error_message = handle_error(f"Invalid report type '{command}'")
        return {"report_path": None, "error_message": error_message, "info_message": None}
    except SystemExit:
        raise
    except ReportError as e:
        error_message = handle_error(e.message)
        if e.usage:
            if e.prefix_usage:
                logger.info(f"\n\nUsage: '{e.usage}'\n")
            else:
                logger.info(f"\n\n{e.usage}\n")
        return {"report_path": None, "error_message": error_message, "info_message": None}
    except Exception as e:
        error_message = handle_error(f"Unexpected error: {str(e)}")
        return {"report_path": None, "error_message": error_message, "info_message": None}
