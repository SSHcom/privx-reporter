"""List reports package."""

import argparse
import logging
from typing import TYPE_CHECKING, Any, cast

from reports._shared.input import BaseReportInputs, get_report_inputs

if TYPE_CHECKING:
    import privx_api

from lib._report.error import handle_error
from lib.utils.config import get_requested_fields, get_subcommand_config, make_report_ids
from lib.utils.output.response import report_response

logger = logging.getLogger(__name__)


def handle(
    api: "privx_api.PrivXAPI",
    args: argparse.Namespace,
    config: dict[str, Any],
    user_group_id: str | None = None,
) -> dict[str, Any]:
    """Route to appropriate list report handler based on subcommand."""
    subcommand = args.subcommand

    # Output configuration for the subcommand
    output_config = get_subcommand_config(config, "list", subcommand)
    # Compute report identifiers (command, subcommand, report_prefix, config_key)
    report_ids = make_report_ids("list", subcommand)
    # Requested fields from CLI --fields option
    requested_fields = get_requested_fields(args, config, report_ids.config_key)

    if requested_fields is not None and len(requested_fields) == 0:
        return report_response(info_message="No fields requested")

    # All list reports use BaseReportInputs (no specific input parameters)
    report_inputs = get_report_inputs(BaseReportInputs, args)

    if report_inputs._error_message:
        return report_response(error_message=report_inputs._error_message)

    # For list commands, default to stdout unless --to-file is specified
    # The CLI parser adds --to-file for list commands instead of --to-stdout
    # The UI explicitly sets to_file=True to ensure file output
    if hasattr(args, "to_file"):
        # If --to-file is specified (or set by UI), write to file (to_stdout=False)
        # Otherwise, default to stdout (to_stdout=True)
        report_inputs.to_stdout = not args.to_file

        # Suppress INFO logging when outputting to stdout to keep output clean
        if report_inputs.to_stdout:
            logging.getLogger().setLevel(logging.WARNING)
    else:
        # Fallback for backward compatibility
        report_inputs.to_stdout = getattr(args, "to_stdout", False)
        if report_inputs.to_stdout:
            logging.getLogger().setLevel(logging.WARNING)

    if subcommand == "access-groups":
        from reports.list.access_groups.report import list_access_groups

        return list_access_groups(
            api,
            output_config,
            report_ids,
            report_inputs,
            requested_fields=requested_fields,
        )
    elif subcommand == "local-users":
        from reports.list.local_users.report import list_local_users

        return list_local_users(
            api,
            output_config,
            report_ids,
            report_inputs,
            requested_fields=requested_fields,
        )
    elif subcommand == "hosts":
        from reports.list.hosts.report import list_hosts

        return list_hosts(
            api,
            output_config,
            report_ids,
            report_inputs,
            requested_fields=requested_fields,
            user_group_id=user_group_id,
        )
    elif subcommand == "network-targets":
        from reports.list.network_targets.report import list_network_targets

        return list_network_targets(
            api,
            output_config,
            report_ids,
            report_inputs,
            requested_fields=requested_fields,
        )
    elif subcommand == "api-targets":
        from reports.list.api_targets.report import list_api_targets

        return list_api_targets(
            api,
            output_config,
            report_ids,
            report_inputs,
            requested_fields=requested_fields,
        )
    elif subcommand == "roles":
        from reports.list.roles.report import list_roles

        return list_roles(
            api,
            output_config,
            report_ids,
            report_inputs,
            requested_fields=requested_fields,
        )
    elif subcommand == "events":
        from reports.list.events.report import list_events

        return list_events(
            api,
            output_config,
            report_ids,
            report_inputs,
            requested_fields=requested_fields,
        )
    elif subcommand == "sources":
        from reports.list.sources.report import list_sources

        return list_sources(
            api,
            output_config,
            report_ids,
            report_inputs,
            requested_fields=requested_fields,
        )
    elif subcommand == "secrets":
        from reports.list.secrets.models import SecretsReportInputs
        from reports.list.secrets.report import list_secrets

        secrets_inputs = get_report_inputs(SecretsReportInputs, args)

        if secrets_inputs._error_message:
            return report_response(error_message=secrets_inputs._error_message)

        secrets_inputs = cast("SecretsReportInputs", secrets_inputs)

        # Apply the same to_stdout logic as other list reports
        if hasattr(args, "to_file"):
            secrets_inputs.to_stdout = not args.to_file
            if secrets_inputs.to_stdout:
                logging.getLogger().setLevel(logging.WARNING)
        else:
            secrets_inputs.to_stdout = getattr(args, "to_stdout", False)
            if secrets_inputs.to_stdout:
                logging.getLogger().setLevel(logging.WARNING)

        return list_secrets(
            api,
            output_config,
            report_ids,
            secrets_inputs,
            requested_fields=requested_fields,
        )
    else:
        error_message = handle_error(
            f"Invalid list report type: {subcommand}",
            (
                "reporter list "
                "<access-groups|local-users|hosts|network-targets|api-targets|"
                "roles|events|sources|secrets> ..."
            ),
        )
        return report_response(error_message=error_message)
