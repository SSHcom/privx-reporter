import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import Select, and_, bindparam, desc, select

from lib._report.error import handle_error
from lib.clients.postgresql import use_database
from lib.database.models.sync.audit_event import AuditEventTable
from lib.env import EnvConfig
from lib.utils.config import get_field_names_and_headers
from lib.utils.config.report_ids import ReportIds
from lib.utils.date import validate_date
from lib.utils.dict import validate_dict_contains
from lib.utils.output.json_writer import JsonWriter
from reports._shared.output import write_report_output
from reports.events._shared.helpers import extract_event_fields, resolve_date_range
from reports.events._shared.models import EventsQueryReportInputs

if TYPE_CHECKING:
    import privx_api

logger = logging.getLogger(__name__)


def _build_query(inputs: EventsQueryReportInputs, from_date: str, to_date: str) -> Select:
    stmt = select(AuditEventTable.c.data)
    conditions = []

    from_dt = validate_date(from_date, "from_date")
    to_dt = validate_date(to_date, "to_date", end_of_day=True)
    conditions.append(AuditEventTable.c.timestamp >= bindparam("from_dt"))
    conditions.append(AuditEventTable.c.timestamp <= bindparam("to_dt"))
    logger.debug(f"Filter: timestamp range {from_dt} to {to_dt}")

    if inputs.event_id:
        escaped_event_id = inputs.event_id.replace("%", r"\%").replace("_", r"\_")
        conditions.append(AuditEventTable.c.data["event_id"].astext.ilike(f"%{escaped_event_id}%"))
        logger.debug(f"Filter: event_id ILIKE '%{escaped_event_id}%'")
    elif inputs.event_name:
        escaped_event_name = inputs.event_name.replace("%", r"\%").replace("_", r"\_")
        conditions.append(AuditEventTable.c.data["event_name"].astext.ilike(f"%{escaped_event_name}%"))
        logger.debug(f"Filter: event_name ILIKE '%{escaped_event_name}%'")

    if conditions:
        stmt = stmt.where(and_(*conditions))

    return stmt.order_by(desc(AuditEventTable.c.timestamp))


def _fetch_events(inputs: EventsQueryReportInputs, from_date: str, to_date: str) -> list[dict[str, Any]]:
    stmt = _build_query(inputs, from_date, to_date)
    from_dt = validate_date(from_date, "from_date")
    to_dt = validate_date(to_date, "to_date", end_of_day=True)
    db = use_database("data")
    rows = db.connection.execute(stmt, {"from_dt": from_dt, "to_dt": to_dt}).fetchall()
    logger.info(f"Fetched {len(rows)} events from database")
    return [row[0] for row in rows]


def _validate_output_records(
    all_event_data: list[dict[str, Any]],
    field_names: list[str],
) -> str | None:
    for idx, data_item in enumerate(all_event_data):
        try:
            validate_dict_contains(data_item, field_names)
        except ValueError as e:
            event_id = data_item.get("event_id", "unknown")
            available_fields = list(data_item.keys())
            return handle_error(
                f"Output configuration validation failed for event {idx + 1} (id: {event_id}): {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file to ensure field names match the data structure.",
            )
    return None


def report_events_by_date_range(
    _api: "privx_api.PrivXAPI",
    inputs: EventsQueryReportInputs,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    requested_fields: list[str] | None = None,
) -> dict[str, Any]:
    if not inputs.event_id and not inputs.event_name:
        return {
            "report_path": None,
            "error_message": "Either --event-id or --event-name must be provided as a filter.",
            "info_message": None,
        }

    if inputs.days and int(inputs.days) > 30:
        return {
            "report_path": None,
            "error_message": "--days cannot exceed 30. Use --from-date and --to-date for longer ranges.",
            "info_message": None,
        }

    from_date, to_date = resolve_date_range(inputs)

    try:
        events = _fetch_events(inputs, from_date, to_date)
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return {
            "report_path": None,
            "error_message": "Database error. Make sure the database is running and accessible.",
            "info_message": None,
        }

    logger.info(f"Applied date range: {from_date} to {to_date}")

    if not events:
        info_message = "No events found matching the specified filters"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    if inputs.json_source:
        report_out_dir = EnvConfig.get_report_out_dir()
        json_writer = JsonWriter(
            name=report_ids.report_prefix,
            output_data=events,
        )

        if inputs.to_stdout:
            json_writer.write_to_stdout()
            return {"report_path": None, "error_message": None, "info_message": None}
        else:
            report_path = json_writer.write_to_file(report_out_dir)
            return {"report_path": report_path, "error_message": None, "info_message": None}

    all_event_data = [extract_event_fields(event) for event in events]

    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    validation_error = _validate_output_records(all_event_data, field_names)
    if validation_error:
        return {"report_path": None, "error_message": validation_error, "info_message": None}

    output_data = [{field: data_item.get(field) for field in field_names} for data_item in all_event_data]

    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, output_data)
