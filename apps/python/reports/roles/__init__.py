# Tests are not necessary for this module.

import argparse
import logging
from typing import TYPE_CHECKING, Any, cast

from reports._shared.input import get_report_inputs
from reports.roles._shared.models import (
    MembersReportInputs,
    QueryReportInputs,
    RestrictionsReportInputs,
    UserReportInputs,
)

if TYPE_CHECKING:
    import privx_api

from lib._report.error import handle_error
from lib.utils.config import get_requested_fields, get_subcommand_config, make_report_ids
from lib.utils.output.response import report_response
from reports.roles.members.report import report_role_members
from reports.roles.query.report import roles_query
from reports.roles.restrictions.report import report_role_restrictions
from reports.roles.user.report import report_user_roles

logger = logging.getLogger(__name__)


def handle(
    api: "privx_api.PrivXAPI",
    args: argparse.Namespace,
    config: dict[str, Any],
    user_group_id: str | None = None,
) -> dict[str, Any]:
    """Route to appropriate roles report handler based on subcommand."""
    subcommand = args.subcommand

    # Output configuration for the subcommand
    output_config = get_subcommand_config(config, "roles", subcommand)
    # Compute report identifiers (command, subcommand, report_prefix, config_key)
    report_ids = make_report_ids("roles", subcommand)
    # Requested fields from CLI --fields option
    requested_fields = get_requested_fields(args, config, report_ids.config_key)

    if requested_fields is not None and len(requested_fields) == 0:
        return report_response(info_message="No fields requested")

    if subcommand == "members":
        report_inputs = get_report_inputs(MembersReportInputs, args)

        if report_inputs._error_message:
            return report_response(error_message=report_inputs._error_message)

        report_inputs = cast("MembersReportInputs", report_inputs)

        return report_role_members(
            api,
            report_inputs,
            output_config,
            report_ids,
            requested_fields=requested_fields,
        )
    elif subcommand == "query":
        report_inputs = get_report_inputs(QueryReportInputs, args)

        if report_inputs._error_message:
            return report_response(error_message=report_inputs._error_message)

        # Cast to specific type after validation
        report_inputs = cast("QueryReportInputs", report_inputs)

        return roles_query(
            api,
            output_config,
            report_ids,
            report_inputs,
            requested_fields=requested_fields,
        )
    elif subcommand == "restrictions":
        report_inputs = get_report_inputs(RestrictionsReportInputs, args)

        if report_inputs._error_message:
            return report_response(error_message=report_inputs._error_message)

        report_inputs = cast("RestrictionsReportInputs", report_inputs)

        return report_role_restrictions(
            api,
            report_inputs,
            output_config,
            report_ids,
            requested_fields,
        )
    elif subcommand == "user":
        report_inputs = get_report_inputs(UserReportInputs, args)

        if report_inputs._error_message:
            return report_response(error_message=report_inputs._error_message)

        report_inputs = cast("UserReportInputs", report_inputs)

        return report_user_roles(
            api,
            report_inputs,
            output_config,
            report_ids,
            requested_fields=requested_fields,
        )
    else:
        error_message = handle_error(
            f"Invalid role report type: {subcommand}",
            "reporter roles <members|query|restrictions|user> ...",
        )
        return report_response(info_message=error_message)
