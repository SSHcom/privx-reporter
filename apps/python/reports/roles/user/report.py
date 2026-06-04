import logging
from typing import Any

import privx_api

from lib import report_api
from lib._report.error import handle_error
from lib.utils.config import get_field_names_and_headers
from lib.utils.config.report_ids import ReportIds
from lib.utils.dict import validate_dict_contains
from reports._shared.output import write_report_output
from reports.roles._shared.helpers import extract_role_restrictions, fetch_access_group_details
from reports.roles._shared.models import UserReportInputs

logger = logging.getLogger(__name__)


def _build_role_record(
    api: privx_api.PrivXAPI,
    user_id: str,
    user_name: str,
    role: dict[str, Any],
) -> dict[str, Any]:
    """Build a single output record combining user, role, access group, and restriction data."""
    access_group_id = role.get("access_group_id", "")
    record = {
        "user_id": user_id,
        "user_name": user_name,
        "role_id": role["id"],
        "role_name": role["name"],
        "access_group_id": access_group_id,
    }
    record.update(fetch_access_group_details(api, access_group_id))
    record.update(extract_role_restrictions(role))
    return record


def _collect_roles_for_user(
    api: privx_api.PrivXAPI,
    user: dict[str, Any],
    user_name: str,
) -> list[dict[str, Any]]:
    """Fetch all roles for a single user and return them as output records."""
    user_id: str = user.get("id") or ""
    found_user_name: str = user.get("principal") or user_name

    logger.info(f"Processing user '{found_user_name}' (ID: {user_id})")

    roles = report_api.get_user_roles(api, user_id)
    logger.info(f"Found {len(roles)} roles for user '{found_user_name}'")

    return [_build_role_record(api, user_id, found_user_name, role) for role in roles]


def _validate_output_roles(
    output_roles: list[dict[str, Any]],
    field_names: list[str],
) -> str | None:
    """Validate that every role record contains all required fields.

    Returns an error message string on the first validation failure, or None if all pass.
    """
    for idx, data_item in enumerate(output_roles):
        try:
            validate_dict_contains(data_item, field_names)
        except ValueError as e:
            role_id = data_item.get("role_id", "unknown")
            role_name = data_item.get("role_name", "unknown")
            available_fields = list(data_item.keys())
            return handle_error(
                f"Output configuration validation failed for role {idx + 1} "
                f"(role_id: {role_id}, role_name: {role_name}): {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file to ensure field names match the data structure.",
            )
    return None


def report_user_roles(
    api: privx_api.PrivXAPI,
    inputs: UserReportInputs,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    requested_fields: list[str] | None = None,
) -> dict[str, Any]:
    """List all roles for every user matching the search term.

    Args:
        api: PrivX API client instance
        inputs: User report inputs containing user name and output options
        output_config: Output configuration dictionary for field selection (from out.toml)
        requested_fields: Optional list of field names from CLI --fields option.
                         If None, uses default field selection from config.
                         If provided, only these fields are included in the specified order.
    """
    user_name = inputs.user_name
    logger.info(f"Searching for users matching '{user_name}'")

    users_response = report_api.users.search_users(api, search_payload={"keywords": user_name})
    users = users_response.get("items", []) if users_response else []

    if not users:
        info_message = f"No users found matching '{user_name}'"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    logger.info(f"Found {len(users)} user(s) matching '{user_name}'")

    output_roles: list[dict[str, Any]] = []
    for user in users:
        output_roles.extend(_collect_roles_for_user(api, user, user_name))

    if not output_roles:
        info_message = f"No roles found for any user matching '{user_name}'"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    if not output_config:
        error_message: str | None = handle_error(
            "Output configuration is required for roles user report",
            "Check your configuration file for the required output settings",
        )
        return {"report_path": None, "error_message": error_message, "info_message": None}

    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    error_message = _validate_output_roles(output_roles, field_names)
    if error_message:
        return {"report_path": None, "error_message": error_message, "info_message": None}

    output_data = [{field: data_item[field] for field in field_names} for data_item in output_roles]

    report_name = f"{report_ids.report_prefix}.{user_name}"

    return write_report_output(report_name, inputs, field_names, header_labels, output_data)
