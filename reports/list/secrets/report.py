import logging
from typing import Any

import privx_api

from lib import report_api
from lib._report.error import handle_error
from lib.utils.config import get_field_names_and_headers
from lib.utils.config.report_ids import ReportIds
from lib.utils.dict import validate_dict_contains
from reports._shared.output import write_report_output
from reports.list.secrets.models import SecretsReportInputs

logger = logging.getLogger(__name__)


def _fetch_all_secrets(api: privx_api.PrivXAPI) -> list[dict[str, Any]]:
    """Paginate through search_secrets to retrieve all secrets."""
    all_items: list[dict[str, Any]] = []
    offset = 0
    batch_size = 200

    while True:
        data = report_api.search_secrets(api, offset=offset, limit=batch_size)
        items = data.get("items", [])
        all_items.extend(items)

        if len(items) < batch_size:
            break
        offset += batch_size

    return all_items


def list_secrets(
    api: privx_api.PrivXAPI,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    inputs: SecretsReportInputs,
    requested_fields: list[str] | None = None,
) -> dict[str, Any]:
    """Query secrets with one row per secret, showing read/write role names.

    Uses search_secrets which returns basic info for all secrets regardless of
    whether the caller has direct access to the secret content.

    Args:
        api: PrivX API client instance
        output_config: Output configuration dictionary (from out.toml)
        report_ids: Report identifiers
        inputs: Filter inputs (name, read_role, write_role substrings)
        requested_fields: Optional list of field names from CLI --fields option
    """
    items = _fetch_all_secrets(api)

    if not items:
        return {"report_path": None, "error_message": None, "info_message": "No secrets found"}

    logger.info(f"Found {len(items)} secrets")

    # Filter by secret name
    if inputs.name:
        name_lower = inputs.name.lower()
        items = [s for s in items if name_lower in s.get("name", "").lower()]
        logger.info(f"Filtered to {len(items)} secrets matching name: {inputs.name}")

    # One row per secret with aggregated role names
    rows: list[dict[str, Any]] = []
    for secret in items:
        read_role_names = sorted({r.get("name", "") for r in secret.get("read_roles", [])})
        write_role_names = sorted({r.get("name", "") for r in secret.get("write_roles", [])})

        # Filter by read_role substring
        if inputs.read_role:
            read_role_lower = inputs.read_role.lower()
            if not any(read_role_lower in name.lower() for name in read_role_names):
                continue

        # Filter by write_role substring
        if inputs.write_role:
            write_role_lower = inputs.write_role.lower()
            if not any(write_role_lower in name.lower() for name in write_role_names):
                continue

        rows.append(
            {
                "name": secret.get("name", ""),
                "read_roles": ", ".join(read_role_names),
                "write_roles": ", ".join(write_role_names),
            }
        )

    if not rows:
        info_message = "No secrets found"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    if not output_config:
        error_message = handle_error(
            "Output configuration is required for list secrets report",
            "Check your configuration file for the required output settings",
        )
        return {"report_path": None, "error_message": error_message, "info_message": None}

    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    for idx, row in enumerate(rows):
        try:
            validate_dict_contains(row, field_names)
        except ValueError as e:
            available_fields = list(row.keys())
            error_message = handle_error(
                f"Output configuration validation failed for row {idx + 1}: {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file to ensure field names match the data structure.",
            )
            return {"report_path": None, "error_message": error_message, "info_message": None}

    output_data = [{field: row[field] for field in field_names} for row in rows]

    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, output_data)
