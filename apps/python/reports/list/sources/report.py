import logging
from typing import Any

import privx_api

from lib._report.error import handle_error
from lib.utils.config import get_field_names_and_headers
from lib.utils.config.report_ids import ReportIds
from lib.utils.dict import validate_dict_contains
from reports._shared.input import BaseReportInputs
from reports._shared.output import write_report_output

logger = logging.getLogger(__name__)


def list_sources(
    api: privx_api.PrivXAPI,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    inputs: BaseReportInputs,
    requested_fields: list[str] | None = None,
) -> dict[str, Any]:
    """List all sources (user directories and host directories) in PrivX."""

    response = api.get_sources()

    if not response.ok:
        error_message = handle_error(
            "Failed to retrieve sources from PrivX API",
            "Check your API connection and permissions",
        )
        return {"report_path": None, "error_message": error_message, "info_message": None}

    sources = response.data.get("items", [])
    logger.info(f"Found {len(sources)} sources")

    if not sources:
        info_message = "No sources found"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    output_data: list[dict[str, Any]] = []
    for source in sources:
        connection = source.get("connection", {})
        connection_type = connection.get("type", "") if isinstance(connection, dict) else ""

        output_data.append(
            {
                "id": source.get("id", ""),
                "name": source.get("name", ""),
                "status_code": source.get("status_code", ""),
                "connection_type": connection_type,
                "enabled": source.get("enabled", False),
            }
        )

    if not output_config:
        error_message = handle_error(
            "Output configuration is required for sources list report",
            "Check your configuration file for the required output settings",
        )
        return {"report_path": None, "error_message": error_message, "info_message": None}

    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    for idx, data_item in enumerate(output_data):
        try:
            validate_dict_contains(data_item, field_names)
        except ValueError as e:
            source_id = data_item.get("id", "unknown")
            source_name = data_item.get("name", "unknown")
            available_fields = list(data_item.keys())
            error_message = handle_error(
                f"Output configuration validation failed for source {idx + 1} "
                f"(id: {source_id}, name: {source_name}): {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file.",
            )
            return {"report_path": None, "error_message": error_message, "info_message": None}

    ordered_output = [{field: data_item[field] for field in field_names} for data_item in output_data]

    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, ordered_output)
