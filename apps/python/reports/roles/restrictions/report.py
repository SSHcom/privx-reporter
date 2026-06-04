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
from reports.roles._shared.models import RestrictionsReportInputs

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


def _has_context_restrictions(role: dict[str, Any]) -> bool:
    """
    Check if a role has contextual restrictions enabled.

    Args:
        role: Role dictionary from the PrivX API

    Returns:
        True if the role has context restrictions enabled, False otherwise
    """
    context = role.get("context", {})
    return bool(context and context.get("enabled", False))


# -----------------------------------------------------------------------------
# Main report function
# -----------------------------------------------------------------------------


def report_role_restrictions(
    api: privx_api.PrivXAPI,
    inputs: RestrictionsReportInputs,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    requested_fields: list[str] | None = None,
) -> dict[str, Any]:
    """List all roles with contextual restrictions enabled.

    Args:
        api: PrivX API client instance
        inputs: Restrictions report inputs containing output options
        output_config: Output configuration dictionary for field selection (from out.toml)
        report_ids: Dictionary containing report_id and config_key (unused in this report but included for consistency)
        requested_fields: Optional list of field names from CLI --fields option.
                         If None, uses default field selection from config.
                         If provided, only these fields are included in the specified order.
    """

    roles = report_api.get_roles(api)
    logger.info(f"Found {len(roles)} roles")

    # Filter roles with context restrictions and extract data
    output_roles: list[dict[str, Any]] = []
    for role in roles:
        if not _has_context_restrictions(role):
            continue

        role_data = {
            "role_id": role["id"],
            "role_name": role["name"],
        }
        restrictions = extract_role_restrictions(role)
        role_data.update(restrictions)
        output_roles.append(role_data)

    logger.info(f"Found {len(output_roles)} roles with context restrictions enabled")

    if not output_roles:
        info_message = "No roles with context restrictions found"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    if not output_config:
        error_message = handle_error(
            "Output configuration is required for roles context-restrict report",
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
