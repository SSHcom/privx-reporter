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


def list_network_targets(
    api: privx_api.PrivXAPI,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    inputs: BaseReportInputs,
    requested_fields: list[str] | None = None,
) -> dict[str, Any]:
    """List all network targets in PrivX.

    Args:
        api: PrivX API client instance
        output_config: Output configuration dictionary for field selection (from out.toml)
        report_ids: Report identifiers
        inputs: Base report inputs containing output options
        requested_fields: Optional list of field names from CLI --fields option.
                         If None, uses default field selection from config.
                         If provided, only these fields are included in the specified order.
    """

    # Get all network targets with automatic pagination
    network_targets = report_api.network_targets.get_all_network_targets(api)
    logger.info(f"Found {len(network_targets)} network targets")

    if not network_targets:
        info_message = "No network targets found"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    # Extract relevant fields
    output_data: list[dict[str, Any]] = []
    for target in network_targets:
        dst = target.get("dst", [])
        first_ip = dst[0]["selector"]["ip"]
        start, end = first_ip["start"], first_ip["end"]

        dst_output = start if start == end else f"{start} --> {end}"

        if len(dst) > 1:
            dst_output += f" ({len(dst)} Destinations)"

        output_data.append(
            {
                "id": target.get("id", ""),
                "name": target.get("name", ""),
                "dst": dst_output,
            }
        )

    if not output_config:
        error_message = handle_error(
            "Output configuration is required for network targets list report",
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
                f"Output configuration validation failed for network target {idx + 1} "
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
