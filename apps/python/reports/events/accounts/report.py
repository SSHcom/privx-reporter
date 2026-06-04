import json
import logging
import re
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
from reports.events._shared.helpers import resolve_date_range
from reports.events._shared.models import EventsAccountsReportInputs

if TYPE_CHECKING:
    import privx_api

logger = logging.getLogger(__name__)

ACCOUNTS_EVENT_ID = "802"
EXCLUDED_MODIFICATION_TOKENS = ("ServiceOptions", "CommandRestrictions")
PRINCIPALS_PATH_RE = re.compile(r"^Principals\.\d+\.(?:Principal|UsernameAttribute|Roles\.\d+\.Name)$")


def _build_query(inputs: EventsAccountsReportInputs, from_date: str, to_date: str) -> Select:
    stmt = select(AuditEventTable.c.data)
    conditions = []

    from_dt = validate_date(from_date, "from_date")
    to_dt = validate_date(to_date, "to_date", end_of_day=True)
    conditions.append(AuditEventTable.c.timestamp >= bindparam("from_dt"))
    conditions.append(AuditEventTable.c.timestamp <= bindparam("to_dt"))
    logger.debug(f"Filter: timestamp range {from_dt} to {to_dt}")

    conditions.append(AuditEventTable.c.data["event_id"].astext == ACCOUNTS_EVENT_ID)
    stmt = stmt.where(and_(*conditions))
    return stmt.order_by(desc(AuditEventTable.c.timestamp))


def _fetch_events(inputs: EventsAccountsReportInputs, from_date: str, to_date: str) -> list[dict[str, Any]]:
    stmt = _build_query(inputs, from_date, to_date)
    from_dt = validate_date(from_date, "from_date")
    to_dt = validate_date(to_date, "to_date", end_of_day=True)
    db = use_database("data")
    rows = db.connection.execute(stmt, {"from_dt": from_dt, "to_dt": to_dt}).fetchall()
    logger.info(f"Fetched {len(rows)} events from database")
    return [row[0] for row in rows]


def _is_802_principal_modification_event(event: dict[str, Any]) -> bool:
    event_id = event.get("event_id")
    if str(event_id) != ACCOUNTS_EVENT_ID:
        return False

    message = event.get("message")
    if not isinstance(message, dict):
        return False

    modifications = message.get("modifications")
    if modifications is None:
        return False

    if isinstance(modifications, str):
        try:
            modifications = json.loads(modifications)
            message["modifications"] = modifications
        except json.JSONDecodeError:
            return False

    if not isinstance(modifications, dict):
        return False

    return any(PRINCIPALS_PATH_RE.match(path) for path in modifications)


def _is_excluded_modification_key(key: str) -> bool:
    return any(token in key for token in EXCLUDED_MODIFICATION_TOKENS)


def _extract_principal_indices(modifications: dict[str, Any]) -> list[str]:
    indices: set[str] = set()
    for key in modifications:
        if _is_excluded_modification_key(key) or not key.startswith("Principals."):
            continue
        parts = key.split(".")
        if len(parts) >= 2 and parts[1].isdigit():
            indices.add(parts[1])
    return sorted(indices, key=int)


def _resolve_change_value(change: dict[str, Any]) -> str:
    new_value = change.get("new_value")
    if new_value not in (None, ""):
        return str(new_value)
    old_value = change.get("old_value")
    if old_value not in (None, ""):
        return str(old_value)
    return ""


def _resolve_action_from_change(change: dict[str, Any]) -> str:
    old_value = change.get("old_value")
    new_value = change.get("new_value")
    if old_value in (None, "") and new_value not in (None, ""):
        return "Added"
    if new_value in (None, "") and old_value not in (None, ""):
        return "Removed"
    if old_value not in (None, "") and new_value not in (None, "") and old_value != new_value:
        return "Modified"
    return ""


def _resolve_action(modifications: dict[str, Any], prefix: str) -> str:
    principal_change = modifications.get(f"{prefix}Principal")
    if isinstance(principal_change, dict):
        principal_action = _resolve_action_from_change(principal_change)
        if principal_action:
            return principal_action

    username_attr_change = modifications.get(f"{prefix}UsernameAttribute")
    if isinstance(username_attr_change, dict):
        username_attr_action = _resolve_action_from_change(username_attr_change)
        if username_attr_action:
            return username_attr_action

    added_count = 0
    removed_count = 0

    for key, value in modifications.items():
        if not key.startswith(prefix) or _is_excluded_modification_key(key):
            continue
        if not isinstance(value, dict):
            continue

        old_value = value.get("old_value")
        new_value = value.get("new_value")
        if old_value in (None, "") and new_value not in (None, ""):
            added_count += 1
        elif new_value in (None, "") and old_value not in (None, ""):
            removed_count += 1

    if added_count and not removed_count:
        return "Added"
    if removed_count and not added_count:
        return "Removed"
    if added_count and removed_count:
        return "Modified"
    return ""


def _resolve_principal_for_action(action: str, primary_change: dict[str, Any], fallback_change: dict[str, Any]) -> str:
    if action == "Removed":
        old_value = primary_change.get("old_value")
        if old_value not in (None, ""):
            return str(old_value)
        fallback_old = fallback_change.get("old_value")
        if fallback_old not in (None, ""):
            return str(fallback_old)

    return _resolve_change_value(primary_change) or _resolve_change_value(fallback_change)


def _resolve_variant(modifications: dict[str, Any], prefix: str) -> str:
    if f"{prefix}Principal" in modifications:
        return "account-explicit"
    if f"{prefix}UsernameAttribute" in modifications or f"{prefix}UseUserAccount" in modifications:
        return "directory"
    return "user-defined"


def _collect_roles(modifications: dict[str, Any], prefix: str, suffix: str) -> str:
    values_by_index: dict[int, str] = {}
    base = f"{prefix}Roles."
    for key, value in modifications.items():
        if _is_excluded_modification_key(key) or not key.startswith(base) or not key.endswith(suffix):
            continue
        if not isinstance(value, dict):
            continue
        parts = key.split(".")
        if len(parts) < 5 or not parts[3].isdigit():
            continue
        role_index = int(parts[3])
        resolved = _resolve_change_value(value)
        if resolved:
            values_by_index[role_index] = resolved
    return "|".join(values_by_index[idx] for idx in sorted(values_by_index))


def _extract_account_changes(event: dict[str, Any]) -> list[dict[str, Any]]:
    message = event.get("message", {})
    modifications = message.get("modifications", {})
    if not isinstance(modifications, dict):
        return []

    principal_indices = _extract_principal_indices(modifications)
    if not principal_indices:
        return []

    results: list[dict[str, Any]] = []
    for principal_index in principal_indices:
        prefix = f"Principals.{principal_index}."
        principal_change = modifications.get(f"{prefix}Principal", {})
        username_attr_change = modifications.get(f"{prefix}UsernameAttribute", {})
        source_change = modifications.get(f"{prefix}Source", {})
        passphrase_change = modifications.get(f"{prefix}Passphrase", {})

        action = _resolve_action(modifications, prefix)
        principal = _resolve_principal_for_action(action, principal_change, username_attr_change)
        source = _resolve_change_value(source_change)
        passphrase_set = isinstance(passphrase_change, dict) and passphrase_change.get("new_value") not in (None, "")

        record = {
            "event_name": event.get("event_name", ""),
            "action": action,
            "variant": _resolve_variant(modifications, prefix),
            "modified_by": message.get("username", ""),
            "timestamp": message.get("timestamp", ""),
            "severity": message.get("severity", ""),
            "host_name": message.get("hostName", ""),
            "principal": principal,
            "role_names": _collect_roles(modifications, prefix, ".Name"),
            "passphrase_set": passphrase_set,
            "message": message.get("message", ""),
            "audit_exposure": message.get("audit-exposure", ""),
            "instance_name": message.get("instanceName", ""),
            "remote_address": message.get("remoteAddress", ""),
            "service_name": event.get("service_name", ""),
            "ssh_privx_service": message.get("SSH-PrivX-service", ""),
            "version": message.get("version", ""),
            "source": source,
            "event_id": event.get("event_id", ""),
            "session_id": message.get("sessionID", ""),
            "access_group_id": message.get("accessGroupID", ""),
            "host_id": message.get("hostID", ""),
            "user_id": message.get("userID", ""),
            "role_ids": _collect_roles(modifications, prefix, ".ID"),
        }
        results.append(record)

    return results


def _validate_output_records(all_event_data: list[dict[str, Any]], field_names: list[str]) -> str | None:
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


def _event_matches_action_filters(event: dict[str, Any], added: bool, removed: bool) -> bool:
    if not (added or removed):
        return True

    changes = _extract_account_changes(event)
    if not changes:
        return False

    if added and not removed:
        return any(str(item.get("action", "")).lower() == "added" for item in changes)
    if removed and not added:
        return any(str(item.get("action", "")).lower() == "removed" for item in changes)
    return True


def report_account_events_by_date_range(
    _api: "privx_api.PrivXAPI",
    inputs: EventsAccountsReportInputs,
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

    filtered_events = [event for event in events if _is_802_principal_modification_event(event)]
    filtered_events = [
        event for event in filtered_events if _event_matches_action_filters(event, inputs.added, inputs.removed)
    ]

    if not filtered_events:
        info_message = "No account addition or removal events found within the specified date range"
        return {"report_path": None, "error_message": None, "info_message": info_message}

    if inputs.json_source:
        report_out_dir = EnvConfig.get_report_out_dir()
        json_writer = JsonWriter(
            name=report_ids.report_prefix,
            output_data=filtered_events,
        )

        if inputs.to_stdout:
            json_writer.write_to_stdout()
            return {"report_path": None, "error_message": None, "info_message": None}
        report_path = json_writer.write_to_file(report_out_dir)
        return {"report_path": report_path, "error_message": None, "info_message": None}

    all_event_data: list[dict[str, Any]] = []
    for event in filtered_events:
        all_event_data.extend(_extract_account_changes(event))

    if not all_event_data:
        info_message = "No account additions or removals found within the specified date range"
        return {"report_path": None, "error_message": None, "info_message": info_message}

    if inputs.added and not inputs.removed:
        all_event_data = [r for r in all_event_data if str(r.get("action", "")).lower() == "added"]
    elif inputs.removed and not inputs.added:
        all_event_data = [r for r in all_event_data if str(r.get("action", "")).lower() == "removed"]

    if not all_event_data:
        info_message = "No account additions or removals found for the selected action filters"
        return {"report_path": None, "error_message": None, "info_message": info_message}

    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    validation_error = _validate_output_records(all_event_data, field_names)
    if validation_error:
        return {"report_path": None, "error_message": validation_error, "info_message": None}

    output_data = [{field: data_item.get(field) for field in field_names} for data_item in all_event_data]
    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, output_data)
