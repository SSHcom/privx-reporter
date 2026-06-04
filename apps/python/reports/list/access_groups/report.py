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


def list_access_groups(
    api: privx_api.PrivXAPI,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    inputs: BaseReportInputs,
    requested_fields: list[str] | None = None,
) -> dict[str, Any]:
    """List all access groups in PrivX.

    Args:
        api: PrivX API client instance
        output_config: Output configuration dictionary for field selection (from out.toml)
        report_ids: Report identifiers
        inputs: Base report inputs containing output options
        requested_fields: Optional list of field names from CLI --fields option.
                         If None, uses default field selection from config.
                         If provided, only these fields are included in the specified order.
    """

    # Get all access groups using search_access_groups
    response = report_api.access_group.search_access_groups(api)

    if not response:
        error_message = handle_error(
            "Failed to retrieve access groups from PrivX API",
            "Check your API connection and permissions",
        )
        return {"report_path": None, "error_message": error_message, "info_message": None}

    access_groups = response.get("items", [])
    logger.info(f"Found {len(access_groups)} access groups")

    if not access_groups:
        info_message = "No access groups found"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    # Extract only the required fields: id, name, comment, default
    output_data: list[dict[str, Any]] = []
    for group in access_groups:
        output_data.append(
            {
                "id": group.get("id", ""),
                "name": group.get("name", ""),
                "comment": group.get("comment", ""),
                "default": group.get("default", False),
            }
        )

    if not output_config:
        error_message = handle_error(
            "Output configuration is required for access groups list report",
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
            group_id = data_item.get("id", "unknown")
            group_name = data_item.get("name", "unknown")
            available_fields = list(data_item.keys())
            error_message = handle_error(
                f"Output configuration validation failed for access group {idx + 1} "
                f"(id: {group_id}, name: {group_name}): {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file to ensure field names match the data structure.",
            )
            return {"report_path": None, "error_message": error_message, "info_message": None}

    # Extract data in the correct order
    ordered_output = [{field: data_item[field] for field in field_names} for data_item in output_data]

    # Write output
    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, ordered_output)
