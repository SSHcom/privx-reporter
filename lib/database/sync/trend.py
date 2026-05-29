"""System trend sync helpers shared by sync server and admin CLI."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import text

from lib.clients.postgresql import use_database
from lib.report_api._shared import get_response_data

logger = logging.getLogger(__name__)

DEFAULT_TREND_DAYS = 90

_ZERO_DATA: dict[str, int] = {
    "roles": 0,
    "local_users": 0,
    "hosts": 0,
    "network_targets": 0,
    "api_targets": 0,
    "access_groups": 0,
    "workflows": 0,
    "secrets": 0,
    "sources": 0,
    "api_clients": 0,
    "hosts_ssh": 0,
    "hosts_rdp": 0,
    "hosts_vnc": 0,
    "hosts_web": 0,
    "hosts_db": 0,
}


@dataclass
class TrendSyncSummary:
    days: int
    placeholder_rows: int
    today_inserted: bool


class TrendAPI(Protocol):
    def get_network_targets(self, *, offset: int, limit: int) -> object: ...
    def get_api_targets(self, *, offset: int, limit: int) -> object: ...
    def get_workflows(self, *, offset: int, limit: int) -> object: ...
    def get_sources(self) -> object: ...
    def get_api_clients(self) -> object: ...


def _safe_api_count(label: str, fn: object) -> int:
    """Call fn and return int result, returning 0 on failure."""
    try:
        return int(fn())  # type: ignore[operator]
    except Exception as exc:
        logger.warning("trend_sync: failed to fetch %s: %s", label, exc)
        return 0


def _fetch_live_counts(api: TrendAPI) -> dict[str, int]:
    """Fetch current entity counts from the PrivX API."""
    from lib import report_api

    def _roles() -> int:
        data = report_api.roles.search_roles(api, search_payload={}, offset=0, limit=1)
        return int((data or {}).get("count", 0))

    def _local_users() -> int:
        data = report_api.users.get_users(api, offset=0, limit=1)
        return int((data or {}).get("count", 0))

    def _hosts() -> int:
        data = report_api.hosts.search_hosts(api, search_payload={}, offset=0, limit=1)
        return int((data or {}).get("count", 0))

    def _network_targets() -> int:
        resp = api.get_network_targets(offset=0, limit=1)
        d = get_response_data(resp, "get_network_targets")
        return int((d or {}).get("count", 0))

    def _api_targets() -> int:
        resp = api.get_api_targets(offset=0, limit=1)
        d = get_response_data(resp, "get_api_targets")
        return int((d or {}).get("count", 0))

    def _access_groups() -> int:
        data = report_api.search_access_groups(api, offset=0, limit=1)
        return int((data or {}).get("count", 0))

    def _workflows() -> int:
        resp = api.get_workflows(offset=0, limit=1)
        d = get_response_data(resp, "get_workflows")
        return int((d or {}).get("count", 0))

    def _secrets() -> int:
        data = report_api.search_secrets(api, offset=0, limit=1)
        return int((data or {}).get("count", 0))

    def _sources() -> int:
        resp = api.get_sources()
        d = get_response_data(resp, "get_sources")
        if d is None:
            return 0
        items = d.get("items", d) if isinstance(d, dict) else d
        return len(items) if isinstance(items, list) else int(d.get("count", 0))

    def _api_clients() -> int:
        resp = api.get_api_clients()
        d = get_response_data(resp, "get_api_clients")
        if d is None:
            return 0
        items = d.get("items", d) if isinstance(d, dict) else d
        return len(items) if isinstance(items, list) else int(d.get("count", 0))

    def _hosts_by_service(service: str) -> int:
        data = report_api.hosts.search_hosts(api, search_payload={"service": [service]}, offset=0, limit=1)
        return int((data or {}).get("count", 0))

    return {
        "roles": _safe_api_count("roles", _roles),
        "local_users": _safe_api_count("local_users", _local_users),
        "hosts": _safe_api_count("hosts", _hosts),
        "network_targets": _safe_api_count("network_targets", _network_targets),
        "api_targets": _safe_api_count("api_targets", _api_targets),
        "access_groups": _safe_api_count("access_groups", _access_groups),
        "workflows": _safe_api_count("workflows", _workflows),
        "secrets": _safe_api_count("secrets", _secrets),
        "sources": _safe_api_count("sources", _sources),
        "api_clients": _safe_api_count("api_clients", _api_clients),
        "hosts_ssh": _safe_api_count("hosts_ssh", lambda: _hosts_by_service("SSH")),
        "hosts_rdp": _safe_api_count("hosts_rdp", lambda: _hosts_by_service("RDP")),
        "hosts_vnc": _safe_api_count("hosts_vnc", lambda: _hosts_by_service("VNC")),
        "hosts_web": _safe_api_count("hosts_web", lambda: _hosts_by_service("WEB")),
        "hosts_db": _safe_api_count("hosts_db", lambda: _hosts_by_service("DB")),
    }


def _fill_missing_days(past_days: int) -> int:
    """Insert zero-value placeholders for missing days in the past."""
    db = use_database("data")
    stmt = text(
        """
        INSERT INTO system_trend ("timestamp", data)
        SELECT
            day,
            CAST(:zero_data AS jsonb)
        FROM generate_series(
            date_trunc('day', now()) - :past_days * interval '1 day',
            date_trunc('day', now()) - interval '1 day',
            interval '1 day'
        ) AS day
        ON CONFLICT ("timestamp") DO NOTHING
        """
    )
    with db.connection.begin():
        result = db.connection.execute(stmt, {"past_days": past_days, "zero_data": json.dumps(_ZERO_DATA)})
    return int(result.rowcount or 0)


def _insert_today_if_missing(api: TrendAPI | None = None) -> bool:
    """Insert today's trend row with live counts if it doesn't already exist."""
    db = use_database("data")

    live_counts = dict(_ZERO_DATA)
    if api is not None:
        try:
            live_counts = _fetch_live_counts(api)
            logger.info("trend_sync: fetched live counts: %s", live_counts)
        except Exception as exc:
            logger.error("trend_sync: failed to fetch live counts: %s", exc)

    stmt = text(
        """
        INSERT INTO system_trend ("timestamp", data)
        VALUES (date_trunc('day', now()), CAST(:data AS jsonb))
        ON CONFLICT ("timestamp") DO NOTHING
        """
    )
    with db.connection.begin():
        existing = db.connection.execute(
            text("""SELECT 1 FROM system_trend WHERE "timestamp" = date_trunc('day', now())""")
        ).fetchone()
        if existing:
            return False
        db.connection.execute(stmt, {"data": json.dumps(live_counts)})
        return True


def run_trend_sync(
    *,
    days: int = DEFAULT_TREND_DAYS,
    api: TrendAPI | None = None,
) -> TrendSyncSummary:
    """Fill missing past days with placeholders and insert today's row if missing.

    Args:
        days: Number of past days to fill with zero placeholders.
        api: PrivX API client. If provided, today's row gets live counts.
    """
    placeholder_rows = _fill_missing_days(days)
    today_inserted = _insert_today_if_missing(api)
    return TrendSyncSummary(
        days=days,
        placeholder_rows=placeholder_rows,
        today_inserted=today_inserted,
    )
