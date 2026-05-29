import logging
from typing import Any

import privx_api

from lib import report_api
from lib._report.error import handle_error
from lib.utils.config import get_field_names_and_headers
from lib.utils.config.report_ids import ReportIds
from lib.utils.dict import validate_dict_contains
from reports._shared.input import BaseReportInputs
from reports._shared.output import write_report_output

logger = logging.getLogger(__name__)


def list_local_users(
    api: privx_api.PrivXAPI,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    inputs: BaseReportInputs,
    requested_fields: list[str] | None = None,
) -> dict[str, Any]:
    """List all local users in PrivX.

    Args:
        api: PrivX API client instance
        output_config: Output configuration dictionary for field selection (from out.toml)
        report_ids: Report identifiers
        inputs: Base report inputs containing output options
        requested_fields: Optional list of field names from CLI --fields option.
                         If None, uses default field selection from config.
                         If provided, only these fields are included in the specified order.
    """

    # Get all users with automatic pagination
    users = report_api.users.get_all_users(api)
    logger.info(f"Found {len(users)} local users")

    if not users:
        info_message = "No local users found"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    # Extract relevant fields
    output_data: list[dict[str, Any]] = []
    for user in users:
        output_data.append(
            {
                "id": user.get("id", ""),
                "username": user.get("username", ""),
                "full_name": user.get("full_name", ""),
                "email": user.get("email", ""),
            }
        )

    if not output_config:
        error_message = handle_error(
            "Output configuration is required for local users list report",
            "Check your configuration file for the required output settings",
        )
        return {"report_path": None, "error_message": error_message, "info_message": None}

    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    # Validate that all data items contain required fields
    for idx, data_item in enumerate(output_data):
        try:
            validate_dict_contains(data_item, field_names)
        except ValueError as e:
            user_id = data_item.get("id", "unknown")
            user_principal = data_item.get("principal", "unknown")
            available_fields = list(data_item.keys())
            error_message = handle_error(
                f"Output configuration validation failed for user {idx + 1} "
                f"(id: {user_id}, principal: {user_principal}): {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file to ensure field names match the data structure.",
            )
            return {"report_path": None, "error_message": error_message, "info_message": None}

    # Extract data in the correct order
    ordered_output = [{field: data_item[field] for field in field_names} for data_item in output_data]

    # Write output
    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, ordered_output)
