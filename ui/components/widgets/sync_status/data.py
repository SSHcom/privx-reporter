from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from lib.clients.postgresql import use_database
from lib.database.models.sync.audit_event import AuditEventTable
from lib.database.models.sync.connection import ConnectionTable
from lib.database.models.sync.system_trend import SystemTrendTable


def _format_ts(value: object) -> str:
    if isinstance(value, datetime):
        return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    return "-"


def _parse_source_config(raw: str | None) -> dict[str, str]:
    if not raw:
        return {"interval_minutes": "-", "range_minutes": "-", "retention_days": "-"}

    parts = [part.strip() for part in raw.split(",")]
    if len(parts) != 3:
        return {"interval_minutes": raw, "range_minutes": "-", "retention_days": "-"}

    return {
        "interval_minutes": parts[0] or "-",
        "range_minutes": parts[1] or "-",
        "retention_days": parts[2] or "-",
    }


def _source_stats(table: object, label: str) -> dict[str, Any]:
    db = use_database("data")
    stmt = select(
        func.count().label("record_count"),
        func.min(table.c.timestamp).label("earliest_record"),
        func.max(table.c.timestamp).label("latest_record"),
    )

    row = db.connection.execute(stmt).one()

    return {
        "source": label,
        "record_count": int(row.record_count or 0),
        "earliest_record": _format_ts(row.earliest_record),
        "latest_record": _format_ts(row.latest_record),
    }


def _sync_configured() -> bool:
    raw = os.getenv("SYNC_SOURCES", "")
    return bool(raw.strip())


def fetch_data() -> dict[str, Any]:
    sync_configured = _sync_configured()
    connection_cfg = (
        _parse_source_config(os.getenv("SYNC_CONNECTION")) if sync_configured else _parse_source_config(None)
    )
    audit_cfg = _parse_source_config(os.getenv("SYNC_AUDIT")) if sync_configured else _parse_source_config(None)
    trend_hour = os.getenv("SYNC_TREND_HOUR", "").strip() if sync_configured else "-"

    return {
        "sources": [
            {
                **_source_stats(ConnectionTable, "connection"),
                "sync_interval_minutes": connection_cfg["interval_minutes"],
                "retention_days": connection_cfg["retention_days"],
            },
            {
                **_source_stats(AuditEventTable, "audit_event"),
                "sync_interval_minutes": audit_cfg["interval_minutes"],
                "retention_days": audit_cfg["retention_days"],
            },
            {
                **_source_stats(SystemTrendTable, "system_trend"),
                "sync_hour_utc": trend_hour or "-",
                "retention_days": "91" if sync_configured else "-",
            },
        ],
        "sync_configured": sync_configured,
        "sync_sources": os.getenv("SYNC_SOURCES", "-"),
        "sync_batch_size": os.getenv("SYNC_BATCH_SIZE", "-"),
        "sync_max_range_hours": os.getenv("SYNC_MAX_RANGE_HOURS", "-"),
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
