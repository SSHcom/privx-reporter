import logging
from typing import Any

import privx_api

from lib import report_api
from lib._report.error import handle_error
from lib.utils.config import get_field_names_and_headers
from lib.utils.config.report_ids import ReportIds
from lib.utils.dict import validate_dict_contains
from reports._shared.output import write_report_output
from reports.roles._shared.helpers import extract_role_restrictions
from reports.roles._shared.models import QueryReportInputs

logger = logging.getLogger(__name__)


def roles_query(
    api: privx_api.PrivXAPI,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    inputs: QueryReportInputs,
    requested_fields: list[str] | None = None,
) -> dict[str, Any]:
    """List all roles in PrivX.

    Args:
        api: PrivX API client instance
        output_config: Output configuration dictionary for field selection (from out.toml)
        report_ids: Report identifiers
        inputs: Query report inputs containing filters and output options
        requested_fields: Optional list of field names from CLI --fields option.
                         If None, uses default field selection from config.
                         If provided, only these fields are included in the specified order.
    """

    if inputs.role_name:
        logger.info(f"Searching for role with exact name '{inputs.role_name}'")
    else:
        logger.info("Searching for all roles")

    # Use get_all_roles (same as list roles) since search_roles may not return access_group_id
    roles = report_api.roles.get_all_roles(api)
    logger.info(f"Found {len(roles)} roles")

    # Apply exact match filter for role_name if specified
    if inputs.role_name:
        role_name_lower = inputs.role_name.lower()
        roles = [r for r in roles if r.get("name", "").lower() == role_name_lower]
        logger.info(f"Exact match filter: {len(roles)} role(s) matching '{inputs.role_name}'")

    # Fetch all access groups once and build a lookup dictionary
    access_groups_response = report_api.access_group.search_access_groups(api)
    access_group_map: dict[str, str] = {}
    if access_groups_response:
        for ag in access_groups_response.get("items", []):
            access_group_map[ag.get("id", "")] = ag.get("name", "")

    output_roles: list[dict[str, Any]] = []

    for role in roles:
        access_group_id = role.get("access_group_id", "")

        role_data = {
            "role_id": role["id"],
            "role_name": role["name"],
            "access_group_id": access_group_id,
            "access_group_name": access_group_map.get(access_group_id, ""),
            "access_group_comment": "",
            "access_group_default": False,
        }

        restrictions = extract_role_restrictions(role)
        role_data.update(restrictions)

        output_roles.append(role_data)

    if inputs.access_group_name:
        access_group_name_lower = inputs.access_group_name.lower()

        output_roles = [r for r in output_roles if access_group_name_lower in r.get("access_group_name", "").lower()]

        logger.info(
            f"Filtered to {len(output_roles)} roles with access group name containing: {inputs.access_group_name}"
        )

    if not output_roles:
        info_message = "No roles found"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    if not output_config:
        error_message = handle_error(
            "Output configuration is required for roles query report",
            "Check your configuration file for the required output settings",
        )
        return {"report_path": None, "error_message": error_message, "info_message": None}

    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    # Validate that all data items contain required fields
    for idx, data_item in enumerate(output_roles):
        try:
            validate_dict_contains(data_item, field_names)
        except ValueError as e:
            role_id = data_item.get("role_id", "unknown")
            role_name = data_item.get("role_name", "unknown")
            available_fields = list(data_item.keys())
            error_message = handle_error(
                f"Output configuration validation failed for role {idx + 1} "
                f"(role_id: {role_id}, role_name: {role_name}): {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file to ensure field names match the data structure.",
            )
            return {"report_path": None, "error_message": error_message, "info_message": None}

    # Extract data in the correct order
    output_data = [{field: data_item[field] for field in field_names} for data_item in output_roles]

    # Write output
    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, output_data)
