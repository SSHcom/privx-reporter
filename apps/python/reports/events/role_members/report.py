import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import Select, and_, bindparam, desc, select

from lib._report.error import handle_error
from lib.clients.postgresql import use_database
from lib.database.models.sync.audit_event import AuditEventTable
from lib.utils.config import get_field_names_and_headers
from lib.utils.config.report_ids import ReportIds
from lib.utils.date import validate_date
from lib.utils.dict import validate_dict_contains
from reports._shared.output import write_report_output
from reports.events._shared.helpers import extract_event_fields, resolve_date_range
from reports.events._shared.models import EventsRoleMembersReportInputs

if TYPE_CHECKING:
    import privx_api

logger = logging.getLogger(__name__)

ROLE_MEMBERS_EVENT_ID = "220"


def _build_query(inputs: EventsRoleMembersReportInputs, from_date: str, to_date: str) -> Select:
    stmt = select(AuditEventTable.c.data)
    conditions = []

    from_dt = validate_date(from_date, "from_date")
    to_dt = validate_date(to_date, "to_date", end_of_day=True)
    conditions.append(AuditEventTable.c.timestamp >= bindparam("from_dt"))
    conditions.append(AuditEventTable.c.timestamp <= bindparam("to_dt"))
    logger.debug(f"Filter: timestamp range {from_dt} to {to_dt}")

    conditions.append(AuditEventTable.c.data["event_id"].astext == ROLE_MEMBERS_EVENT_ID)
    stmt = stmt.where(and_(*conditions))
    return stmt.order_by(desc(AuditEventTable.c.timestamp))


def _fetch_events(inputs: EventsRoleMembersReportInputs, from_date: str, to_date: str) -> list[dict[str, Any]]:
    stmt = _build_query(inputs, from_date, to_date)
    from_dt = validate_date(from_date, "from_date")
    to_dt = validate_date(to_date, "to_date", end_of_day=True)
    db = use_database("data")
    rows = db.connection.execute(stmt, {"from_dt": from_dt, "to_dt": to_dt}).fetchall()
    logger.info(f"Fetched {len(rows)} events from database")
    return [row[0] for row in rows]


def _extract_role_changes(event: dict[str, Any], base_fields: dict[str, Any]) -> list[dict[str, Any]]:
    message = event.get("message", {})
    user_id = message.get("targetUserID", "")
    modifications = message.get("modifications", {})
    roles_mod = modifications.get("Roles", {})

    old_value = roles_mod.get("old_value", [])
    new_value = roles_mod.get("new_value", [])

    old_role_ids = {role.get("id") for role in old_value if role.get("id")}
    new_role_ids = {role.get("id") for role in new_value if role.get("id")}

    added_ids = new_role_ids - old_role_ids
    removed_ids = old_role_ids - new_role_ids

    old_roles_by_id = {role.get("id"): role for role in old_value if role.get("id")}
    new_roles_by_id = {role.get("id"): role for role in new_value if role.get("id")}

    base_fields["modified_by"] = message.get("username", "")
    base_fields["username"] = message.get("principal", "")

    results = []

    for role_id in added_ids:
        role = new_roles_by_id.get(role_id, {})
        record = base_fields.copy()
        record["action"] = "add"
        record["user_id"] = user_id
        record["user_name"] = message.get("principal", "")
        record["role_id"] = role_id
        record["role_name"] = role.get("name", "")
        record["grant_type"] = role.get("grant_type", "")
        results.append(record)

    for role_id in removed_ids:
        role = old_roles_by_id.get(role_id, {})
        record = base_fields.copy()
        record["action"] = "remove"
        record["user_id"] = user_id
        record["user_name"] = message.get("principal", "")
        record["role_id"] = role_id
        record["role_name"] = role.get("name", "")
        record["grant_type"] = role.get("grant_type", "")
        results.append(record)

    return results


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


def report_role_member_events_by_date_range(
    _api: "privx_api.PrivXAPI",
    inputs: EventsRoleMembersReportInputs,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    requested_fields: list[str] | None = None,
) -> dict[str, Any]:
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
        info_message = "No role member addition or removal events found within the specified date range"
        return {"report_path": None, "error_message": None, "info_message": info_message}

    all_event_data = []
    for event in events:
        base_fields = extract_event_fields(event)
        role_changes = _extract_role_changes(event, base_fields)
        all_event_data.extend(role_changes)

    if not all_event_data:
        info_message = "No role member additions or removals found within the specified date range"
        return {"report_path": None, "error_message": None, "info_message": info_message}

    if inputs.added and not inputs.removed:
        all_event_data = [r for r in all_event_data if r.get("action") == "add"]
    elif inputs.removed and not inputs.added:
        all_event_data = [r for r in all_event_data if r.get("action") == "remove"]

    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    validation_error = _validate_output_records(all_event_data, field_names)
    if validation_error:
        return {"report_path": None, "error_message": validation_error, "info_message": None}

    output_data = [{field: data_item.get(field) for field in field_names} for data_item in all_event_data]

    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, output_data)
