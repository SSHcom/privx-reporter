import logging
from typing import Any

import privx_api

from lib import report_api
from lib._report.error import handle_error
from lib.utils.config import get_field_names_and_headers
from lib.utils.config.report_ids import ReportIds
from lib.utils.dict import validate_dict_contains
from reports._shared.access_group import resolve_allowed_access_group_ids
from reports._shared.input import BaseReportInputs
from reports._shared.output import write_report_output

logger = logging.getLogger(__name__)


def list_hosts(
    api: privx_api.PrivXAPI,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    inputs: BaseReportInputs,
    requested_fields: list[str] | None = None,
    user_group_id: str | None = None,
) -> dict[str, Any]:
    """List all hosts in PrivX.

    Args:
        api: PrivX API client instance
        output_config: Output configuration dictionary for field selection (from out.toml)
        report_ids: Report identifiers
        inputs: Base report inputs containing output options
        requested_fields: Optional list of field names from CLI --fields option.
                         If None, uses default field selection from config.
                         If provided, only these fields are included in the specified order.
    """

    # Get all hosts with automatic pagination
    hosts = report_api.hosts.get_all_hosts(api)
    logger.info(f"Found {len(hosts)} hosts")

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

        hosts = [
            host
            for host in hosts
            if isinstance(host.get("access_group_id"), str) and host["access_group_id"] in allowed_access_group_ids
        ]
        logger.info("Access group filter applied: %s host(s) remain", len(hosts))

    if not hosts:
        info_message = "No hosts found"
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
    for host in hosts:
        addresses = host.get("addresses", [])
        addresses_str = ",".join(addresses) if addresses else ""
        services = host.get("services", [])
        services_str = ",".join(item.get("service", "") for item in services if "service" in item)
        principals = host.get("principals", [])
        principals_str = ",".join(item.get("principal", "") for item in principals if "principal" in item)

        access_group_id = host.get("access_group_id", "")
        access_group_name = access_group_map.get(access_group_id, "")

        output_data.append(
            {
                "id": host.get("id", ""),
                "common_name": host.get("common_name", ""),
                "addresses": addresses_str,
                "access_group_id": access_group_id,
                "access_group_name": access_group_name,
                "comment": host.get("comment", ""),
                "audit_enabled": host.get("audit_enabled", ""),
                "password_rotation_enabled": host.get("password_rotation_enabled", ""),
                "source_id": host.get("source_id", ""),
                "services": services_str,
                "principals": principals_str,
            }
        )

    if not output_config:
        error_message = handle_error(
            "Output configuration is required for hosts list report",
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
            host_id = data_item.get("id", "unknown")
            host_name = data_item.get("common_name", "unknown")
            available_fields = list(data_item.keys())
            error_message = handle_error(
                f"Output configuration validation failed for host {idx + 1} "
                f"(id: {host_id}, common_name: {host_name}): {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file to ensure field names match the data structure.",
            )
            return {"report_path": None, "error_message": error_message, "info_message": None}

    # Extract data in the correct order
    ordered_output = [{field: data_item[field] for field in field_names} for data_item in output_data]

    # Write output
    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, ordered_output)
