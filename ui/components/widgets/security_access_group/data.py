from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import String, and_, case, func, literal, not_, or_, select
from streamlit.logger import get_logger

from lib.clients.postgresql import use_database
from lib.database.models.sync.connection import ConnectionTable

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection
    from sqlalchemy.sql.elements import ColumnElement
    from sqlalchemy.sql.selectable import Subquery

logger = get_logger(__name__)

_DEFAULT_DAYS = 30
_MAX_SAFE_DAYS = 30
_MAX_ROWS_TO_SCAN = 100_000


def _json_text(path: str) -> ColumnElement[str]:
    return ConnectionTable.c.data.op("#>>")(path)


def _limited_connection_ids(start_ts: datetime) -> Subquery:
    return (
        select(ConnectionTable.c.record_id)
        .where(ConnectionTable.c.timestamp >= start_ts)
        .limit(_MAX_ROWS_TO_SCAN)
        .subquery()
    )


def _limited_scope(start_ts: datetime) -> Subquery:
    limited_ids = _limited_connection_ids(start_ts)

    return (
        select(
            ConnectionTable.c.record_id.label("record_id"),
            ConnectionTable.c.timestamp.label("timestamp"),
            ConnectionTable.c.data.label("data"),
        )
        .where(ConnectionTable.c.record_id.in_(select(limited_ids.c.record_id)))
        .subquery()
    )


def _json_text_from(scope: Subquery, path: str) -> ColumnElement[str]:
    return scope.c.data.op("#>>")(path)


def _build_base_result(safe_days: int, now: datetime) -> dict[str, Any]:
    return {
        "label": "Security & Access Control",
        "description": "Credential posture from recent connection records.",
        "days": safe_days,
        "row_limit": _MAX_ROWS_TO_SCAN,
        "standing_credentials": 0,
        "jit_credentials": 0,
        "break_glass_access": 0,
        "analyzed_connections": 0,
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


def _fetch_security_counts(sql_connection: Connection, scope: Subquery) -> dict[str, int]:
    data_text = func.lower(func.cast(ConnectionTable.c.data, String))

    jit_expr = or_(
        data_text.like("%jit%"),
        data_text.like("%just_in_time%"),
        data_text.like("%justintime%"),
    )

    break_glass_expr = or_(
        data_text.like("%break_glass%"),
        data_text.like("%breakglass%"),
        data_text.like("%break-glass%"),
        data_text.like("%break glass%"),
        data_text.like("%emergency_access%"),
        data_text.like("%emergency%"),
        data_text.like("%privileged_override%"),
    )

    credential_expr = or_(
        func.nullif(func.trim(_json_text_from(scope, "{target_host_account}")), "").is_not(None),
        data_text.like("%credential%"),
        data_text.like("%principal%"),
        data_text.like("%target_host_account%"),
        data_text.like("%account%"),
    )

    standing_expr = and_(
        credential_expr,
        not_(jit_expr),
        not_(break_glass_expr),
    )

    stmt = select(
        func.count().label("analyzed_connections"),
        func.coalesce(func.sum(case((standing_expr, 1), else_=0)), literal(0)).label("standing_credentials"),
        func.coalesce(func.sum(case((jit_expr, 1), else_=0)), literal(0)).label("jit_credentials"),
        func.coalesce(func.sum(case((break_glass_expr, 1), else_=0)), literal(0)).label("break_glass_access"),
    ).select_from(scope)

    row = sql_connection.execute(stmt).one()

    return {
        "analyzed_connections": int(row.analyzed_connections or 0),
        "standing_credentials": int(row.standing_credentials or 0),
        "jit_credentials": int(row.jit_credentials or 0),
        "break_glass_access": int(row.break_glass_access or 0),
    }


def fetch_data(days: int = _DEFAULT_DAYS) -> dict[str, Any]:
    started_at = time.perf_counter()

    requested_days = max(1, int(days))
    safe_days = min(_MAX_SAFE_DAYS, requested_days)

    now = datetime.now(UTC)
    start_ts = now - timedelta(days=safe_days)

    base_result = _build_base_result(safe_days, now)

    logger.info(
        "security_access_group.fetch_data start sql_aggregation=true days=%s requested_days=%s max_rows=%s start_ts=%s",
        safe_days,
        requested_days,
        _MAX_ROWS_TO_SCAN,
        start_ts.isoformat(),
    )

    try:
        db = use_database("data")
        scope = _limited_scope(start_ts)

        with db.engine.connect() as sql_connection:
            counts = _fetch_security_counts(sql_connection, scope)

    except Exception:
        logger.exception(
            "security_access_group.fetch_data failed total_elapsed=%.2fs",
            time.perf_counter() - started_at,
        )
        return {
            **base_result,
            "error": "Security & Access Control data could not be loaded. Check server logs for details.",
            "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

    result = {
        **base_result,
        **counts,
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    warnings: list[str] = []

    if requested_days > _MAX_SAFE_DAYS:
        warnings.append(
            f"Showing last {_MAX_SAFE_DAYS} days instead of requested "
            f"{requested_days} days to protect database performance."
        )

    warnings.append(
        f"Analytics is limited to at most {_MAX_ROWS_TO_SCAN:,} matching rows to protect database performance."
    )

    result["warning"] = " ".join(warnings)

    logger.info(
        "security_access_group.fetch_data done sql_aggregation=true "
        "analyzed_connections=%s standing=%s jit=%s break_glass=%s max_rows=%s total_elapsed=%.2fs",
        result["analyzed_connections"],
        result["standing_credentials"],
        result["jit_credentials"],
        result["break_glass_access"],
        _MAX_ROWS_TO_SCAN,
        time.perf_counter() - started_at,
    )

    return result
