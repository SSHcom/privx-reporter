from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import desc, func, literal, or_, select
from streamlit.logger import get_logger

from lib.clients.postgresql import use_database
from lib.database.models.sync.connection import ConnectionTable

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection
    from sqlalchemy.sql.elements import ColumnElement
    from sqlalchemy.sql.selectable import Subquery

_DEFAULT_TOP_N = 10
_DEFAULT_DAYS = 7
_MAX_SAFE_DAYS = 7
_MAX_ROWS_TO_SCAN = 100_000

logger = get_logger(__name__)

UEBA_LABEL_PATHS = (
    "{ueba,label}",
    "{ueba_label}",
    "{risk,label}",
    "{risk,ueba,label}",
)

USER_PATHS = (
    "{  user,display_name}",
    "{user_data,display_name}",
    "{display_name}",
    "{user_data,full_name}",
    "{user,name}",
    "{user,username}",
    "{user_data,principal}",
    "{user_data,email}",
    "{username}",
    "{principal}",
    "{source_user}",
    "{user,id}",
)

API_MARKER_PATHS = (
    "{connection_type}",
    "{auth_method}",
    "{authentication_method}",
    "{source_type}",
    "{login_method}",
)

TARGET_ACCOUNT_PATHS = (
    "{target_host_account}",
    "{target_account}",
    "{target,account}",
    "{account}",
    "{principal}",
)

HOST_NAME_PATHS = (
    "{target_host,name}",
    "{target,name}",
    "{host,name}",
    "{hostname}",
)

HOST_ADDRESS_PATHS = (
    "{target_host,address}",
    "{target_host,ip}",
    "{target,address}",
    "{host,address}",
    "{host,ip}",
    "{ip}",
)

HOST_UUID_PATHS = (
    "{target_host,id}",
    "{target_host,uuid}",
    "{target,id}",
    "{host,uuid}",
    "{host,id}",
)


def _json_text(path: str) -> ColumnElement[str]:
    return ConnectionTable.c.data.op("#>>")(path)


def _first_non_empty_json_text(paths: tuple[str, ...], fallback: str = "Unknown") -> ColumnElement[str]:
    values = [func.nullif(func.trim(_json_text(path)), "") for path in paths]
    return func.coalesce(*values, literal(fallback))


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


def _first_non_empty_json_text_from(
    scope: Subquery,
    paths: tuple[str, ...],
    fallback: str = "Unknown",
) -> ColumnElement[str]:
    values = [func.nullif(func.trim(_json_text_from(scope, path)), "") for path in paths]
    return func.coalesce(*values, literal(fallback))


def _build_base_result(safe_days: int, safe_top_n: int, now: datetime) -> dict[str, Any]:
    return {
        "label": "Behavior & Risk Analytics",
        "description": "UEBA markers and top identities from recent connections.",
        "days": safe_days,
        "top_n": safe_top_n,
        "row_limit": _MAX_ROWS_TO_SCAN,
        "connections_ueba_usual": 0,
        "connections_ueba_anomaly": 0,
        "top_privx_users": [],
        "top_api_users": [],
        "top_target_accounts": [],
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


def _fetch_ueba_counts(sql_connection: Connection, scope: Subquery) -> tuple[int, int]:
    label_expr = func.lower(_first_non_empty_json_text(UEBA_LABEL_PATHS, fallback=""))

    stmt = (
        select(
            label_expr.label("ueba_label"),
            func.count().label("connections"),
        )
        .select_from(scope)
        .group_by(label_expr)
    )

    usual_count = 0
    anomaly_count = 0

    for row in sql_connection.execute(stmt):
        label = str(row.ueba_label or "").strip().lower()
        count = int(row.connections or 0)

        if label == "usual":
            usual_count += count
        elif label == "anomaly":
            anomaly_count += count

    return usual_count, anomaly_count


def _fetch_top_privx_users(
    sql_connection: Connection,
    *,
    scope: Subquery,
    safe_top_n: int,
) -> list[dict[str, Any]]:
    user_expr = _first_non_empty_json_text_from(scope, USER_PATHS)

    stmt = (
        select(
            user_expr.label("user"),
            func.count().label("connections"),
        )
        .select_from(scope)
        .group_by(user_expr)
        .order_by(desc("connections"), user_expr.asc())
        .limit(safe_top_n)
    )

    return [
        {
            "User": str(row.user or "Unknown"),
            "Connections": int(row.connections or 0),
        }
        for row in sql_connection.execute(stmt)
    ]


def _fetch_top_api_users(
    sql_connection: Connection,
    *,
    scope: Subquery,
    safe_top_n: int,
) -> list[dict[str, Any]]:
    user_expr = _first_non_empty_json_text_from(scope, USER_PATHS)

    api_marker_exprs = [
        func.lower(func.coalesce(func.nullif(func.trim(_json_text_from(scope, path)), ""), ""))
        for path in API_MARKER_PATHS
    ]

    api_filter = or_(
        *[expr.in_(("api", "apikey", "api_key", "token", "access_token", "bearer")) for expr in api_marker_exprs]
    )

    stmt = (
        select(
            user_expr.label("api_user"),
            func.count().label("connections"),
        )
        .select_from(scope)
        .where(api_filter)
        .group_by(user_expr)
        .order_by(desc("connections"), user_expr.asc())
        .limit(safe_top_n)
    )

    return [
        {
            "API User": str(row.api_user or "Unknown"),
            "Connections": int(row.connections or 0),
        }
        for row in sql_connection.execute(stmt)
    ]


def _fetch_top_target_account_summaries(
    sql_connection: Connection,
    *,
    scope: Subquery,
    safe_top_n: int,
) -> list[tuple[str, int]]:
    account_expr = _first_non_empty_json_text_from(scope, TARGET_ACCOUNT_PATHS)

    stmt = (
        select(
            account_expr.label("target_account"),
            func.count().label("connections"),
        )
        .select_from(scope)
        .group_by(account_expr)
        .order_by(desc("connections"), account_expr.asc())
        .limit(safe_top_n)
    )

    return [
        (
            str(row.target_account or "Unknown"),
            int(row.connections or 0),
        )
        for row in sql_connection.execute(stmt)
    ]


def _fetch_top_hosts_for_target_account(
    sql_connection: Connection,
    *,
    scope: Subquery,
    target_account: str,
) -> list[tuple[str, str, str, int]]:
    account_expr = _first_non_empty_json_text_from(scope, TARGET_ACCOUNT_PATHS)
    host_name_expr = _first_non_empty_json_text_from(scope, HOST_NAME_PATHS, fallback="-")
    host_address_expr = _first_non_empty_json_text_from(scope, HOST_ADDRESS_PATHS, fallback="-")
    host_uuid_expr = _first_non_empty_json_text_from(scope, HOST_UUID_PATHS, fallback="-")

    stmt = (
        select(
            host_name_expr.label("host_name"),
            host_address_expr.label("host_address"),
            host_uuid_expr.label("host_uuid"),
            func.count().label("connections"),
        )
        .select_from(scope)
        .where(account_expr == target_account)
        .group_by(host_name_expr, host_address_expr, host_uuid_expr)
        .order_by(
            desc("connections"),
            host_name_expr.asc(),
            host_address_expr.asc(),
            host_uuid_expr.asc(),
        )
        .limit(3)
    )

    return [
        (
            str(row.host_name or "-"),
            str(row.host_address or "-"),
            str(row.host_uuid or "-"),
            int(row.connections or 0),
        )
        for row in sql_connection.execute(stmt)
    ]


def _fetch_top_target_accounts(
    sql_connection: Connection,
    *,
    scope: Subquery,
    safe_top_n: int,
) -> list[dict[str, Any]]:
    summaries = _fetch_top_target_account_summaries(
        sql_connection,
        scope=scope,
        safe_top_n=safe_top_n,
    )

    rows: list[dict[str, Any]] = []

    for account, count in summaries:
        top_hosts = _fetch_top_hosts_for_target_account(
            sql_connection,
            scope=scope,
            target_account=account,
        )

        host_detail_parts = [
            f"{name} | {address} | {host_uuid} ({host_count})" for name, address, host_uuid, host_count in top_hosts
        ]

        rows.append(
            {
                "Target Account": account,
                "Connections": count,
                "Host Detail": ", ".join(host_detail_parts) if top_hosts else "-",
                "Host Names": ", ".join(name for name, _, _, _ in top_hosts) if top_hosts else "-",
                "Host IPs": ", ".join(address for _, address, _, _ in top_hosts) if top_hosts else "-",
                "Host UUIDs": ", ".join(host_uuid for _, _, host_uuid, _ in top_hosts) if top_hosts else "-",
            }
        )

    return rows


def fetch_data(
    days: int = _DEFAULT_DAYS,
    top_n: int = _DEFAULT_TOP_N,
    batch_size: int = 1000,
) -> dict[str, Any]:
    started_at = time.perf_counter()

    requested_days = max(1, int(days))
    safe_days = min(_MAX_SAFE_DAYS, requested_days)
    safe_top_n = max(1, int(top_n))

    now = datetime.now(UTC)
    start_ts = now - timedelta(days=safe_days)

    logger.info(
        "behavior_risk.fetch_data start sql_aggregation=true days=%s requested_days=%s "
        "top_n=%s batch_size_ignored=%s max_rows=%s start_ts=%s",
        safe_days,
        requested_days,
        safe_top_n,
        batch_size,
        _MAX_ROWS_TO_SCAN,
        start_ts.isoformat(),
    )

    base_result = _build_base_result(safe_days, safe_top_n, now)

    try:
        db_started_at = time.perf_counter()
        db = use_database("data")
        logger.info(
            "behavior_risk.fetch_data database_ready elapsed=%.2fs",
            time.perf_counter() - db_started_at,
        )

        scope = _limited_scope(start_ts)

        with db.engine.connect() as sql_connection:
            ueba_started_at = time.perf_counter()
            usual_count, anomaly_count = _fetch_ueba_counts(sql_connection, scope)
            logger.info(
                "behavior_risk.fetch_data ueba_counts_done usual=%s anomaly=%s elapsed=%.2fs",
                usual_count,
                anomaly_count,
                time.perf_counter() - ueba_started_at,
            )

            users_started_at = time.perf_counter()
            top_privx_users = _fetch_top_privx_users(
                sql_connection,
                scope=scope,
                safe_top_n=safe_top_n,
            )
            logger.info(
                "behavior_risk.fetch_data top_privx_users_done rows=%s elapsed=%.2fs",
                len(top_privx_users),
                time.perf_counter() - users_started_at,
            )

            api_users_started_at = time.perf_counter()
            top_api_users = _fetch_top_api_users(
                sql_connection,
                scope=scope,
                safe_top_n=safe_top_n,
            )
            logger.info(
                "behavior_risk.fetch_data top_api_users_done rows=%s elapsed=%.2fs",
                len(top_api_users),
                time.perf_counter() - api_users_started_at,
            )

            target_accounts_started_at = time.perf_counter()
            top_target_accounts = _fetch_top_target_accounts(
                sql_connection,
                scope=scope,
                safe_top_n=safe_top_n,
            )
            logger.info(
                "behavior_risk.fetch_data top_target_accounts_done rows=%s elapsed=%.2fs",
                len(top_target_accounts),
                time.perf_counter() - target_accounts_started_at,
            )

    except Exception:
        logger.exception(
            "behavior_risk.fetch_data failed total_elapsed=%.2fs",
            time.perf_counter() - started_at,
        )
        return {
            **base_result,
            "error": "Behavior risk analytics could not be loaded. Check server logs for details.",
            "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

    result = {
        **base_result,
        "connections_ueba_usual": usual_count,
        "connections_ueba_anomaly": anomaly_count,
        "top_privx_users": top_privx_users,
        "top_api_users": top_api_users,
        "top_target_accounts": top_target_accounts,
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

    if warnings:
        result["warning"] = " ".join(warnings)

    logger.info(
        "behavior_risk.fetch_data done sql_aggregation=true usual=%s anomaly=%s "
        "top_users=%s top_api_users=%s top_target_accounts=%s max_rows=%s total_elapsed=%.2fs",
        usual_count,
        anomaly_count,
        len(top_privx_users),
        len(top_api_users),
        len(top_target_accounts),
        _MAX_ROWS_TO_SCAN,
        time.perf_counter() - started_at,
    )

    return result
