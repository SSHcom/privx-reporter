import logging
from typing import Any

import privx_api

from lib import report_api
from lib._report.error import handle_error
from lib.env import EnvConfig
from lib.utils.config import get_field_names_and_headers
from lib.utils.config.report_ids import ReportIds
from lib.utils.dict import validate_dict_contains
from lib.utils.string import sanitize_string
from reports._shared.output import write_report_output
from reports.roles._shared.helpers import fetch_access_group_details
from reports.roles._shared.models import MembersReportInputs

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


def _fetch_role_members_paginated(api: privx_api.PrivXAPI, role_id: str) -> list[dict[str, Any]]:
    """
    Fetch all members for a role with pagination.

    Args:
        api: PrivX API client instance
        role_id: Role ID to fetch members for

    Returns:
        List of all members for the role
    """
    batch_size = EnvConfig.get_api_batchsize()
    offset = 0
    all_members = []

    while True:
        response = report_api.get_role_members(api, role_id=role_id, offset=offset, limit=batch_size)
        members = response.get("items", [])
        if not members:
            break

        all_members.extend(members)

        # Check if we've fetched all members
        total_count = response.get("count", 0)
        if len(all_members) >= total_count:
            break

        offset += batch_size

    logger.debug(f"Fetched {len(all_members)} members for role {role_id}")
    return all_members


# -----------------------------------------------------------------------------
# Main report function
# -----------------------------------------------------------------------------


def report_role_members(
    api: privx_api.PrivXAPI,
    inputs: MembersReportInputs,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    requested_fields: list[str] | None = None,
) -> dict[str, Any]:
    """List all members having a PrivX role.

    Args:
        api: PrivX API client instance
        inputs: Members report inputs containing role name and output options
        output_config: Output configuration dictionary for field selection (from out.toml)
        requested_fields: Optional list of field names from CLI --fields option.
                         If None, uses default field selection from config.
                         If provided, only these fields are included in the specified order.
    """
    if not inputs.role_name or not inputs.role_name.strip():
        error_message = handle_error("'role' cannot be empty")
        return {"report_path": None, "error_message": error_message, "info_message": None}

    all_roles = report_api.get_roles(api)

    # Filter by role_name
    all_roles = [role for role in all_roles if role["name"] == inputs.role_name]
    if not all_roles:
        info_message = f"Role '{inputs.role_name}' not found"
        logger.error(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    logger.info(f"Filtering by role: {inputs.role_name}")

    if not output_config:
        error_message = handle_error(
            "Output configuration is required for roles members report",
            "Check your configuration file for the required output settings",
        )
        return {"report_path": None, "error_message": error_message, "info_message": None}

    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    # Extract member field names (excluding role_id, role_name, and access group fields which are added separately)
    member_field_names = [
        field
        for field in field_names
        if field not in ("role_id", "role_name", "access_group_id", "access_group_name", "access_group_comment")
    ]

    all_formatted_members: list[dict[str, Any]] = []

    for role in all_roles:
        role_id = role["id"]
        current_role_name = role["name"]
        access_group_id = role.get("access_group_id", "")

        # Fetch access group details
        access_group_details = fetch_access_group_details(api, access_group_id)

        # Fetch all members for this role with pagination
        all_members = _fetch_role_members_paginated(api, role_id)

        # Format each member with role_id, role_name, access group info and specified fields
        for member in all_members:
            formatted_member = {
                "role_id": role_id,
                "role_name": current_role_name,
                "access_group_id": access_group_id,
                "access_group_name": access_group_details["access_group_name"],
                "access_group_comment": access_group_details["access_group_comment"],
            }
            # Map 'id' from API to 'user_id' in output
            for field_name in member_field_names:
                if field_name == "user_id":
                    formatted_member[field_name] = member.get("id", "")
                else:
                    formatted_member[field_name] = member.get(field_name, "")
            all_formatted_members.append(formatted_member)

    logger.info(f"Found {len(all_formatted_members)} members")

    if not all_formatted_members:
        info_message = "No members found"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    # Validate that all data items contain required fields
    for idx, data_item in enumerate(all_formatted_members):
        try:
            validate_dict_contains(data_item, field_names)
        except ValueError as e:
            role_name_val = data_item.get("role_name", "unknown")
            principal = data_item.get("principal", "unknown")
            available_fields = list(data_item.keys())
            error_message = handle_error(
                f"Output configuration validation failed for member {idx + 1} "
                f"(role: {role_name_val}, principal: {principal}): {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file to ensure field names match the data structure.",
            )
            return {"report_path": None, "error_message": error_message, "info_message": None}

    # Extract data in the correct order
    output_data = [{field: data_item[field] for field in field_names} for data_item in all_formatted_members]

    sanitized_role_name = sanitize_string(inputs.role_name)
    report_name = f"{report_ids.report_prefix}.{sanitized_role_name}"

    # Write output
    return write_report_output(report_name, inputs, field_names, header_labels, output_data)
