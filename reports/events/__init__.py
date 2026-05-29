# Tests are not necessary for this module.

import argparse
import logging
from typing import TYPE_CHECKING, Any, cast

from lib._report.generator import UIListResponse
from reports._shared.input import get_report_inputs
from reports.events._shared.models import (
    EventsAccountsReportInputs,
    EventsQueryReportInputs,
    EventsRoleMembersReportInputs,
)

if TYPE_CHECKING:
    import privx_api

from lib._report.error import handle_error
from lib.utils.config import get_requested_fields, get_subcommand_config, make_report_ids
from lib.utils.output.response import report_response
from reports.events.accounts.report import report_account_events_by_date_range
from reports.events.query.report import report_events_by_date_range
from reports.events.query.ui import get_list as get_query_list
from reports.events.role_members.report import report_role_member_events_by_date_range

logger = logging.getLogger(__name__)


def get_list(subcommand: str, list_key: str) -> "UIListResponse":
    """Route UI list requests to the appropriate subcommand handler.

    Args:
        subcommand: The report subcommand (e.g., "query")
        list_key: The list key to retrieve (e.g., "event_names")

    Returns:
        UIListResponse with values or error_message
    """
    if subcommand == "query":
        return get_query_list(list_key)
    elif subcommand in {"role-members", "accounts"}:
        return UIListResponse(
            values=[],
            error_message=f"Subcommand '{subcommand}' does not support UI lists",
        )
    else:
        return UIListResponse(
            values=[],
            error_message=f"Unknown subcommand: '{subcommand}'",
        )


def handle(
    api: "privx_api.PrivXAPI",
    args: argparse.Namespace,
    config: dict[str, Any],
    user_group_id: str | None = None,
) -> dict[str, Any]:
    """Route to appropriate events report handler based on subcommand."""
    subcommand = args.subcommand

    output_config = get_subcommand_config(config, "events", subcommand)
    report_ids = make_report_ids("events", subcommand)
    requested_fields = get_requested_fields(args, config, report_ids.config_key)

    if requested_fields is not None and len(requested_fields) == 0:
        return report_response(info_message="No fields requested")

    if subcommand == "query":
        report_inputs = get_report_inputs(EventsQueryReportInputs, args)

        if report_inputs._error_message:
            return report_response(error_message=report_inputs._error_message)

        report_inputs = cast("EventsQueryReportInputs", report_inputs)

        return report_events_by_date_range(
            api,
            report_inputs,
            output_config,
            report_ids,
            requested_fields=requested_fields,
        )
    elif subcommand == "role-members":
        report_inputs = get_report_inputs(EventsRoleMembersReportInputs, args)

        if report_inputs._error_message:
            return report_response(error_message=report_inputs._error_message)

        report_inputs = cast("EventsRoleMembersReportInputs", report_inputs)

        return report_role_member_events_by_date_range(
            api,
            report_inputs,
            output_config,
            report_ids,
            requested_fields=requested_fields,
        )
    elif subcommand == "accounts":
        report_inputs = get_report_inputs(EventsAccountsReportInputs, args)

        if report_inputs._error_message:
            return report_response(error_message=report_inputs._error_message)

        report_inputs = cast("EventsAccountsReportInputs", report_inputs)

        return report_account_events_by_date_range(
            api,
            report_inputs,
            output_config,
            report_ids,
            requested_fields=requested_fields,
        )
    else:
        error_message = handle_error(
            f"Invalid events report type: {subcommand}",
            "reporter events <query|accounts|role-members> ...",
        )
        return report_response(info_message=error_message)
