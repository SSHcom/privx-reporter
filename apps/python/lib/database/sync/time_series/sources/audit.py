"""Audit event sync source implementation."""

from __future__ import annotations

import json
import logging
import re
from hashlib import sha256
from typing import Any

from sqlalchemy import select

import lib.report_api as report_api
from lib.clients.postgresql import use_database
from lib.database.models.admin.audit_event_sync_table import AuditEventSyncTable
from lib.database.models.sync.audit_event import AuditEventTable
from lib.database.sync.time_series.protocol import FetchResult

logger = logging.getLogger(__name__)

PRINCIPALS_PATH_RE = re.compile(r"^Principals\.\d+\.(?:Principal|UsernameAttribute|Roles\.\d+\.Name)$")


def _normalize_modifications(event: dict[str, Any]) -> None:
    message = event.get("message")
    if not isinstance(message, dict):
        return

    modifications = message.get("modifications")
    if not isinstance(modifications, str):
        return

    try:
        message["modifications"] = json.loads(modifications)
    except json.JSONDecodeError:
        logger.warning("Unable to parse audit event modifications as JSON")


def _get_enabled_event_ids() -> set[str]:
    admin_db = use_database("admin")
    rows = admin_db.connection.execute(
        select(AuditEventSyncTable.c.code).where(AuditEventSyncTable.c.enabled.is_(True))
    ).fetchall()
    return {str(row[0]) for row in rows}


def _is_802_principal_modification_event(event: dict[str, Any]) -> bool:
    event_id = event.get("event_id")
    if str(event_id) != "802":
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


def _build_audit_record_id(event: dict[str, Any]) -> str:
    canonical_event = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return sha256(canonical_event.encode("utf-8")).hexdigest()


def _resolve_enabled_event_ids(context: object) -> set[str]:
    """Coerce runtime context to a typed set of event IDs."""
    if not isinstance(context, set):
        return set()

    return {str(value) for value in context}


class AuditEventSync:
    """Sync source for PrivX audit events."""

    table = AuditEventTable
    timestamp_key = "created"
    name = "audit events"

    def prepare(self, api: object) -> set[str]:
        del api
        return _get_enabled_event_ids()

    def fetch_batch(
        self,
        api: object,
        start_time: str,
        end_time: str,
        offset: int,
        limit: int,
    ) -> FetchResult:
        data = report_api.get_audit_events(
            api,
            start_time,
            end_time,
            offset=offset,
            limit=limit,
            propagate_errors=True,
        )
        return FetchResult(items=data["items"], count=len(data["items"]), total_count=data.get("count"))

    def filter_item(self, item: dict[str, Any], context: object) -> bool:
        enabled_event_ids = _resolve_enabled_event_ids(context)
        event_id = str(item.get("event_id")) if item.get("event_id") is not None else None
        return event_id in enabled_event_ids or _is_802_principal_modification_event(item)

    def normalize_item(self, item: dict[str, Any]) -> None:
        _normalize_modifications(item)

    def build_record_id(self, item: dict[str, Any]) -> str | None:
        return _build_audit_record_id(item)

    def build_row_extras(self, item: dict[str, Any]) -> dict[str, Any]:
        event_id = str(item.get("event_id")) if item.get("event_id") is not None else None
        return {"event_id": event_id, "event_name": item.get("event_name")}
