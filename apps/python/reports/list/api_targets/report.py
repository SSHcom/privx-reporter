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


def list_api_targets(
    api: privx_api.PrivXAPI,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    inputs: BaseReportInputs,
    requested_fields: list[str] | None = None,
) -> dict[str, Any]:
    """List all API targets in PrivX.

    Args:
        api: PrivX API client instance
        output_config: Output configuration dictionary for field selection (from out.toml)
        report_ids: Report identifiers
        inputs: Base report inputs containing output options
        requested_fields: Optional list of field names from CLI --fields option.
                         If None, uses default field selection from config.
                         If provided, only these fields are included in the specified order.
    """

    # Get all API targets with automatic pagination
    api_targets = report_api.api_targets.get_all_api_targets(api)
    logger.info(f"Found {len(api_targets)} API targets")

    if not api_targets:
        info_message = "No API targets found"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    # Fetch all access groups once and build a lookup dictionary
    access_groups_response = report_api.access_group.search_access_groups(api)
    access_group_map: dict[str, str] = {}
    if access_groups_response:
        for ag in access_groups_response.get("items", []):
            access_group_map[ag.get("id", "")] = ag.get("name", "")

    # Extract relevant fields
    output_data: list[dict[str, Any]] = []
    for target in api_targets:
        authorized_endpoints = target.get("authorized_endpoints", [])
        authorized_endpoints_str = ",".join(item.get("host", "") for item in authorized_endpoints if "host" in item)

        access_group_id = target.get("access_group_id", "")
        access_group_name = access_group_map.get(access_group_id, "")

        output_data.append(
            {
                "id": target.get("id", ""),
                "name": target.get("name", ""),
                "comment": target.get("comment", ""),
                "audit_enabled": target.get("audit_enabled", ""),
                "access_group_id": access_group_id,
                "access_group_name": access_group_name,
                "tls_insecure_skip_verify": target.get("tls_insecure_skip_verify", ""),
                "authorized_endpoints": authorized_endpoints_str,
            }
        )

    if not output_config:
        error_message = handle_error(
            "Output configuration is required for API targets list report",
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
            target_id = data_item.get("id", "unknown")
            target_name = data_item.get("name", "unknown")
            available_fields = list(data_item.keys())
            error_message = handle_error(
                f"Output configuration validation failed for API target {idx + 1} "
                f"(id: {target_id}, name: {target_name}): {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file to ensure field names match the data structure.",
            )
            return {"report_path": None, "error_message": error_message, "info_message": None}

    # Extract data in the correct order
    ordered_output = [{field: data_item[field] for field in field_names} for data_item in output_data]

    # Write output
    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, ordered_output)
