# Tests are not necessary for this module.

import argparse
import logging
from typing import TYPE_CHECKING, Any, cast

from reports._shared.input import get_report_inputs
from reports.connections._shared.models import DetailsReportInputs, QueryReportInputs

if TYPE_CHECKING:
    import privx_api

from lib._report.error import handle_error
from lib.utils.config import get_requested_fields, get_subcommand_config, make_report_ids
from lib.utils.output.response import report_response
from reports.connections.details.report import report_connection_details
from reports.connections.query.report import report_connections_query
from reports.connections.query_db.report import report_connections_db_query

logger = logging.getLogger(__name__)


def handle(
    api: "privx_api.PrivXAPI",
    args: argparse.Namespace,
    config: dict[str, Any],
    user_group_id: str | None = None,
) -> dict[str, Any]:
    """Route to appropriate connections report handler based on subcommand."""
    subcommand = args.subcommand

    try:
        # Output configuration for the subcommand
        output_config = get_subcommand_config(config, "connections", subcommand)
        # Compute report identifiers (command, subcommand, report_prefix, config_key)
        report_ids = make_report_ids("connections", subcommand)

        # Requested fields from CLI --fields option
        requested_fields = get_requested_fields(args, config, report_ids.config_key)

        if requested_fields is not None and len(requested_fields) == 0:
            return report_response(info_message="No fields requested")

        if subcommand == "details":
            report_inputs = get_report_inputs(DetailsReportInputs, args)

            if report_inputs._error_message:
                return report_response(error_message=report_inputs._error_message)

            report_inputs = cast("DetailsReportInputs", report_inputs)

            return report_connection_details(
                api,
                report_inputs,
                output_config,
                report_ids,
                requested_fields=requested_fields,
                user_group_id=user_group_id,
            )
        elif subcommand == "query":
            report_inputs = get_report_inputs(QueryReportInputs, args)

            if report_inputs._error_message:
                return report_response(error_message=report_inputs._error_message)

            report_inputs = cast("QueryReportInputs", report_inputs)

            return report_connections_query(
                api,
                report_inputs,
                output_config,
                report_ids,
                requested_fields=requested_fields,
                user_group_id=user_group_id,
            )

        elif subcommand == "query-db":
            report_inputs = get_report_inputs(QueryReportInputs, args)

            if report_inputs._error_message:
                return report_response(error_message=report_inputs._error_message)

            report_inputs = cast("QueryReportInputs", report_inputs)

            return report_connections_db_query(
                api,
                report_inputs,
                output_config,
                report_ids,
                requested_fields=requested_fields,
                user_group_id=user_group_id,
            )
        else:
            error_message = handle_error(
                f"Invalid connection report type: {subcommand}",
                "reporter connections <details|query> ...",
            )
            return report_response(info_message=error_message)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return report_response(error_message=str(e))
