import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import privx_api

from lib import report_api
from lib._report.error import handle_error
from lib.env import EnvConfig
from lib.utils.config import get_field_names_and_headers
from lib.utils.config.report_ids import ReportIds
from lib.utils.dict import validate_dict_contains
from lib.utils.output.json_writer import JsonWriter
from reports._shared.access_group import resolve_allowed_access_group_ids
from reports._shared.output import write_report_output
from reports.connections._shared import extract_target_ips
from reports.connections._shared.models import DetailsReportInputs

logger = logging.getLogger(__name__)


def _resolve_connection_access_group_id(
    api: "privx_api.PrivXAPI",
    connection_data: dict[str, Any],
) -> str | None:
    """Resolve access group ID for the connection's target host."""
    candidates = (
        connection_data.get("access_group_id"),
        connection_data.get("target_host_data", {}).get("access_group_id"),
        connection_data.get("target_host", {}).get("access_group_id"),
    )
    for access_group_id in candidates:
        if isinstance(access_group_id, str) and access_group_id:
            return access_group_id

    target_host_id = connection_data.get("target_host", {}).get("id")
    if not isinstance(target_host_id, str) or not target_host_id:
        return None

    try:
        host_data = report_api.hosts.get_host(api, target_host_id)
    except Exception as e:
        logger.warning("Failed to resolve host details for '%s': %s", target_host_id, str(e))
        return None

    host_access_group_id = host_data.get("access_group_id")
    if isinstance(host_access_group_id, str) and host_access_group_id:
        return host_access_group_id

    return None


def _extract_connection_fields(connection_data: dict[str, Any], api: "privx_api.PrivXAPI") -> dict[str, Any]:
    """Extract and format connection fields for output.

    Args:
        connection_data: Raw connection data from API
        api: PrivX API client instance for user lookup

    Returns:
        Dictionary with formatted connection fields
    """
    # Resolve username (prefer full_name, fall back to principal)
    user_id = connection_data.get("user", {}).get("id", "")
    user_name = ""
    if user_id:
        try:
            user = report_api.get_user_by_id(api, user_id)
            if user:
                user_name = user.get("full_name") or user.get("principal") or ""
        except Exception as e:
            logger.warning(
                "Failed to resolve user details for connection '%s': %s",
                connection_data.get("id", ""),
                str(e),
            )

    # Extract authorized endpoints from target_api_data
    authorized_endpoints_list = connection_data.get("target_api_data", {}).get("authorized_endpoints") or []
    authorized_endpoints = ", ".join(
        endpoint.get("host", "") for endpoint in authorized_endpoints_list if endpoint.get("host")
    )

    # Extract target IPs from target_network_data
    dst_list = connection_data.get("target_network_data", {}).get("dst")
    target_ips = extract_target_ips(dst_list)

    return {
        "connection_id": connection_data.get("id", ""),
        "created": connection_data.get("created", ""),
        "connected": connection_data.get("connected", ""),
        "disconnected": connection_data.get("disconnected", ""),
        "duration": connection_data.get("duration", ""),
        "status": connection_data.get("status", ""),
        "type": connection_data.get("type", ""),
        "authorized_endpoints": authorized_endpoints,
        "user_id": user_id,
        "user_name": user_name,
        "user_display_name": connection_data.get("user", {}).get("display_name", ""),
        "target_host_id": connection_data.get("target_host", {}).get("id", ""),
        "target_host_address": connection_data.get("target_host_address", ""),
        "target_host_common_name": connection_data.get("target_host", {}).get("common_name", ""),
        "target_host_account": connection_data.get("target_host_account", ""),
        "target_ips": target_ips,
    }


# -----------------------------------------------------------------------------
# Main report function
# -----------------------------------------------------------------------------


def report_connection_details(
    api: "privx_api.PrivXAPI",
    inputs: DetailsReportInputs,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    requested_fields: list[str] | None = None,
    user_group_id: str | None = None,
) -> dict[str, Any]:
    """Get connection details by ID and save as JSON or CSV.

    Args:
        api: PrivX API client instance
        inputs: Details report inputs containing connection_id and output options
        output_config: Output configuration dictionary for field selection (only used for CSV and 'to-json' output)
        requested_fields: Optional list of field names from CLI --fields option.
                         If None, uses default field selection from config.
                         If provided, only these fields are included in the specified order.
    """
    report_out_dir = EnvConfig.get_report_out_dir()
    logger.info(f"Fetching connection details for ID: {inputs.connection_id}")

    # Get connection details
    connection_data = report_api.get_connection(api, inputs.connection_id)

    if not connection_data:
        info_message = f"No connection data returned for ID '{inputs.connection_id}'. The connection may not exist."
        logger.warning(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    if user_group_id is not None:
        allowed_access_group_ids, resolution_error = resolve_allowed_access_group_ids(api, user_group_id)
        if resolution_error:
            return {"report_path": None, "error_message": resolution_error, "info_message": None}
        if allowed_access_group_ids is None:
            return {
                "report_path": None,
                "error_message": "Failed to resolve allowed access groups",
                "info_message": None,
            }

        connection_access_group_id = _resolve_connection_access_group_id(api, connection_data)
        if (
            not isinstance(connection_access_group_id, str)
            or connection_access_group_id not in allowed_access_group_ids
        ):
            info_message = f"No connection data returned for ID '{inputs.connection_id}'. The connection may not exist."
            logger.warning("Connection '%s' filtered by access group policy", inputs.connection_id)
            return {"report_path": None, "error_message": None, "info_message": info_message}

    logger.info("Successfully fetched connection details")

    # Handle json_source special case (output original API response)
    if inputs.json_source:
        # JSON output: use original JSON as-is (no field selection)
        # Wrap in list as JsonWriter expects a list
        json_writer = JsonWriter(
            name=f"{report_ids.report_prefix}-{inputs.connection_id}",
            output_data=[connection_data],
        )

        if inputs.to_stdout:
            # Write to stdout
            json_writer.write_to_stdout()
            return {"report_path": None, "error_message": None, "info_message": None}
        else:
            # Write to file
            report_path = json_writer.write_to_file(report_out_dir)
            return {"report_path": report_path, "error_message": None, "info_message": None}

    # Extract and format connection fields
    output_connection = _extract_connection_fields(connection_data, api)

    # Validate output configuration
    if not output_config:
        error_message = handle_error(
            "Output configuration is required for connections details report",
            "Check your configuration file for the required output settings",
        )
        return {"report_path": None, "error_message": error_message, "info_message": None}

    # Get field configuration
    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    # Validate that data contains required fields
    try:
        validate_dict_contains(output_connection, field_names)
    except ValueError as e:
        connection_id_val = output_connection.get("connection_id", "unknown")
        available_fields = list(output_connection.keys())
        error_message = handle_error(
            f"Output configuration validation failed for connection (id: {connection_id_val}): {str(e)}",
            f"Available fields in data: {available_fields}\n"
            f"Required fields from config: {field_names}\n\n"
            "Please check your output configuration file to ensure field names match the data structure.",
        )
        return {"report_path": None, "error_message": error_message, "info_message": None}

    # Extract data in the correct order
    output_data = [{field: output_connection[field] for field in field_names}]
    report_name = f"{report_ids.report_prefix}.{inputs.connection_id}"

    # Write output
    return write_report_output(
        report_name,
        inputs,
        field_names,
        header_labels,
        output_data,
    )
