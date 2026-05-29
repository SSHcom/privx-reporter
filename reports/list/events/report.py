import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from lib._report.error import handle_error
from lib.clients.postgresql import use_database
from lib.database.models.sync.audit_event import AuditEventTable
from lib.utils.config import get_field_names_and_headers
from lib.utils.config.report_ids import ReportIds
from lib.utils.dict import validate_dict_contains
from reports._shared.input import BaseReportInputs
from reports._shared.output import write_report_output

if TYPE_CHECKING:
    import privx_api

logger = logging.getLogger(__name__)


def _fetch_unique_events() -> list[dict[str, Any]]:
    db = use_database("data")
    stmt = (
        select(
            AuditEventTable.c.event_id,
            AuditEventTable.c.event_name,
        )
        .where(AuditEventTable.c.event_id.is_not(None))
        .distinct()
        .order_by(AuditEventTable.c.event_id)
    )
    rows = db.connection.execute(stmt).fetchall()
    logger.info(f"Fetched {len(rows)} unique event types from database")
    return [{"event_id": row.event_id, "event_name": row.event_name} for row in rows]


def list_events(
    _api: "privx_api.PrivXAPI",
    output_config: dict[str, Any],
    report_ids: ReportIds,
    inputs: BaseReportInputs,
    requested_fields: list[str] | None = None,
) -> dict[str, Any]:
    try:
        events = _fetch_unique_events()
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return {
            "report_path": None,
            "error_message": "Database error. Make sure the database is running and accessible.",
            "info_message": None,
        }

    if not events:
        info_message = "No events found in database"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    if not output_config:
        error_message = handle_error(
            "Output configuration is required for events list report",
            "Check your configuration file for the required output settings",
        )
        return {"report_path": None, "error_message": error_message, "info_message": None}

    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    for idx, data_item in enumerate(events):
        try:
            validate_dict_contains(data_item, field_names)
        except ValueError as e:
            event_id = data_item.get("event_id", "unknown")
            available_fields = list(data_item.keys())
            error_message = handle_error(
                f"Output configuration validation failed for event {idx + 1} (id: {event_id}): {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file to ensure field names match the data structure.",
            )
            return {"report_path": None, "error_message": error_message, "info_message": None}

    ordered_output = [{field: data_item[field] for field in field_names} for data_item in events]

    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, ordered_output)
