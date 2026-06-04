import argparse
import logging
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import privx_api

from lib._report.error import handle_error
from lib.utils.config import get_requested_fields, get_subcommand_config, make_report_ids
from lib.utils.output.response import report_response
from reports._shared.input import get_report_inputs
from reports.access._shared.models import (
    AccountReportInputs,
    AccountRestrictionsReportInputs,
    HostsReportInputs,
    QueryReportInputs,
    RoleMapReportInputs,
)
from reports.access.account.report import report_account_access
from reports.access.account_restrictions.report import report_account_restrictions
from reports.access.hosts.report import report_hosts_access
from reports.access.query.report import report_access_query
from reports.access.role_map.report import report_user_role_access_map

logger = logging.getLogger(__name__)


def handle(
    api: "privx_api.PrivXAPI",
    args: argparse.Namespace,
    config: dict[str, Any],
    user_group_id: str | None = None,
) -> dict[str, Any]:
    """Route to appropriate access report handler based on subcommand."""
    subcommand = args.subcommand

    # Output configuration for the subcommand
    output_config = get_subcommand_config(config, "access", subcommand)
    # Compute report identifiers (command, subcommand, report_prefix, config_key)
    report_ids = make_report_ids("access", subcommand)
    # Requested fields from CLI --fields option
    requested_fields = get_requested_fields(args, config, report_ids.config_key)

    if requested_fields is not None and len(requested_fields) == 0:
        return report_response(info_message="No fields requested")

    if subcommand == "account":
        report_inputs = get_report_inputs(AccountReportInputs, args)

        if report_inputs._error_message:
            return report_response(error_message=report_inputs._error_message)

        report_inputs = cast("AccountReportInputs", report_inputs)

        return report_account_access(
            api,
            report_inputs,
            output_config,
            report_ids,
            requested_fields,
            user_group_id=user_group_id,
        )
    elif subcommand == "account-restrictions":
        report_inputs = get_report_inputs(AccountRestrictionsReportInputs, args)

        if report_inputs._error_message:
            return report_response(error_message=report_inputs._error_message)

        report_inputs = cast("AccountRestrictionsReportInputs", report_inputs)

        return report_account_restrictions(
            api,
            report_inputs,
            output_config,
            report_ids,
            requested_fields,
            user_group_id=user_group_id,
        )
    elif subcommand == "hosts":
        report_inputs = get_report_inputs(HostsReportInputs, args)

        if report_inputs._error_message:
            return report_response(error_message=report_inputs._error_message)

        report_inputs = cast("HostsReportInputs", report_inputs)

        return report_hosts_access(
            api,
            report_inputs,
            output_config,
            report_ids,
            requested_fields,
            user_group_id=user_group_id,
        )
    elif subcommand == "role-map":
        report_inputs = get_report_inputs(RoleMapReportInputs, args)

        if report_inputs._error_message:
            return report_response(error_message=report_inputs._error_message)

        report_inputs = cast("RoleMapReportInputs", report_inputs)

        return report_user_role_access_map(
            api,
            report_inputs,
            output_config,
            report_ids,
            requested_fields,
            user_group_id=user_group_id,
        )
    elif subcommand == "query":
        report_inputs = get_report_inputs(QueryReportInputs, args)

        if report_inputs._error_message:
            return report_response(error_message=report_inputs._error_message)

        report_inputs = cast("QueryReportInputs", report_inputs)

        return report_access_query(
            api,
            report_inputs,
            output_config,
            report_ids,
            requested_fields,
            user_group_id=user_group_id,
        )

    else:
        error_message = handle_error(
            f"Invalid access report type: {subcommand}",
            "reporter access <account|account-restrictions|hosts|query|role-map> ...",
        )
        return report_response(info_message=error_message)
