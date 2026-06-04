"""Query-based connections report from database.

This report queries the TimescaleDB connection table using the same filters
as the API-based query report:
- timestamp column for date range (from/to)
- JSONB operators for all other filters (type, host address/name/account, user name)
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import privx_api

from sqlalchemy import Select, and_, bindparam, desc, or_, select

from lib._report.error import handle_error
from lib.clients.postgresql import use_database
from lib.database.models.sync.connection import ConnectionTable
from lib.utils.config import get_field_names_and_headers
from lib.utils.config.report_ids import ReportIds
from lib.utils.date import validate_date
from lib.utils.dict import validate_dict_contains
from reports._shared.access_group import resolve_allowed_access_group_ids
from reports._shared.output import write_report_output
from reports.connections._shared.models import QueryReportInputs
from reports.connections._shared.query_reports_helpers import extract_connection_fields

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================


def _build_query(
    inputs: QueryReportInputs,
    allowed_access_group_ids: set[str] | None = None,
) -> Select:
    """
    Build a SQLAlchemy SELECT for the connection table applying all active filters.

    Date range filters on the timestamp column; all other filters use JSONB
    path operators with ILIKE for case-insensitive substring matching.

    Args:
        inputs: Query report inputs containing filter values

    Returns:
        SQLAlchemy Select statement
    """
    stmt = select(ConnectionTable.c.data)
    conditions = []

    if inputs.from_date and inputs.to_date:
        from_dt = validate_date(inputs.from_date, "from_date")
        to_dt = validate_date(inputs.to_date, "to_date", end_of_day=True)
        conditions.append(ConnectionTable.c.timestamp >= bindparam("from_dt"))
        conditions.append(ConnectionTable.c.timestamp <= bindparam("to_dt"))
        logger.debug(f"Filter: timestamp range {from_dt} to {to_dt}")

    if inputs.connection_type:
        escaped = inputs.connection_type.replace("%", r"\%").replace("_", r"\_")
        conditions.append(ConnectionTable.c.data["type"].astext.ilike(f"%{escaped}%"))
        logger.debug(f"Filter: type ILIKE '%{escaped}%'")

    if inputs.target_address:
        escaped = inputs.target_address.replace("%", r"\%").replace("_", r"\_")
        conditions.append(ConnectionTable.c.data["target_host_address"].astext.ilike(f"%{escaped}%"))
        logger.debug(f"Filter: target_host_address ILIKE '%{escaped}%'")

    if inputs.target_account:
        escaped = inputs.target_account.replace("%", r"\%").replace("_", r"\_")
        conditions.append(ConnectionTable.c.data["target_host_account"].astext.ilike(f"%{escaped}%"))
        logger.debug(f"Filter: target_host_account ILIKE '%{escaped}%'")

    if inputs.user_name:
        escaped = inputs.user_name.replace("%", r"\%").replace("_", r"\_")
        conditions.append(
            or_(
                ConnectionTable.c.data[("user_data", "full_name")].astext.ilike(f"%{escaped}%"),
                ConnectionTable.c.data[("user_data", "principal")].astext.ilike(f"%{escaped}%"),
            )
        )
        logger.debug(f"Filter: user_data.full_name or principal ILIKE '%{escaped}%'")

    if allowed_access_group_ids is not None:
        conditions.append(ConnectionTable.c.data["access_group_id"].astext.in_(sorted(allowed_access_group_ids)))
        logger.debug("Filter: access_group_id IN (resolved user group access groups)")

    if conditions:
        stmt = stmt.where(and_(*conditions))

    return stmt.order_by(desc(ConnectionTable.c.timestamp))


def _fetch_connections(
    inputs: QueryReportInputs,
    allowed_access_group_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Execute the query and return raw connection data dicts.

    Args:
        inputs: Query report inputs

    Returns:
        List of raw connection dicts from the JSONB data column
    """
    stmt = _build_query(inputs, allowed_access_group_ids=allowed_access_group_ids)
    db = use_database("data")

    # Build bind params for date range if present
    params: dict[str, str] = {}
    if inputs.from_date and inputs.to_date:
        params["from_dt"] = validate_date(inputs.from_date, "from_date")
        params["to_dt"] = validate_date(inputs.to_date, "to_date", end_of_day=True)

    rows = db.connection.execute(stmt, params).fetchall()
    logger.info(f"Fetched {len(rows)} connections from database")
    return [row[0] for row in rows]


# ============================================================================
# Output Validation
# ============================================================================


def _validate_output_records(
    all_connection_data: list[dict[str, Any]],
    field_names: list[str],
) -> str | None:
    """
    Validate that all records contain required fields.

    Args:
        all_connection_data: List of connection records
        field_names: Required field names from output config

    Returns:
        Error message string if validation fails, None otherwise
    """
    for idx, data_item in enumerate(all_connection_data):
        try:
            validate_dict_contains(data_item, field_names)
        except ValueError as e:
            connection_id = data_item.get("connection_id", "unknown")
            available_fields = list(data_item.keys())
            return handle_error(
                f"Output configuration validation failed for connection {idx + 1} (id: {connection_id}): {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file to ensure field names match the data structure.",
            )
    return None


# ============================================================================
# Main Report Function
# ============================================================================


def report_connections_db_query(
    _api: "privx_api.PrivXAPI",
    inputs: QueryReportInputs,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    requested_fields: list[str] | None = None,
    user_group_id: str | None = None,
) -> dict[str, Any]:
    """
    Generate filtered connections report from the TimescaleDB connection table.

    Args:
        api: PrivX API client instance (unused; kept for interface consistency)
        inputs: Query report inputs containing filter options and output settings
        output_config: Output configuration dictionary for field selection (from out.toml)
        report_ids: Precomputed report identifiers (prefix and config key)
        requested_fields: Optional list of field names from CLI --fields option

    Returns:
        dict with keys: report_path, error_message, info_message
    """

    allowed_access_group_ids: set[str] | None = None
    if user_group_id is not None:
        allowed_access_group_ids, resolution_error = resolve_allowed_access_group_ids(_api, user_group_id)
        if resolution_error:
            return {
                "report_path": None,
                "error_message": resolution_error,
                "info_message": None,
            }

    try:
        connections = _fetch_connections(inputs, allowed_access_group_ids=allowed_access_group_ids)
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return {
            "report_path": None,
            "error_message": "Database error. Make sure the database is running and accessible.",
            "info_message": None,
        }

    if not connections:
        info_message = "No connections found matching the specified filters"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    all_connection_data = [extract_connection_fields(conn) for conn in connections]

    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    validation_error = _validate_output_records(all_connection_data, field_names)
    if validation_error:
        return {"report_path": None, "error_message": validation_error, "info_message": None}

    output_data = [{field: data_item[field] for field in field_names} for data_item in all_connection_data]

    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, output_data)
