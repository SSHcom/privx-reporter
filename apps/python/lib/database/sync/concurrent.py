"""Concurrent stats sync — captures session and connection counts every minute."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy.dialects.postgresql import insert as pg_insert

from lib.clients.postgresql import use_database
from lib.database.models.sync.concurrent_stats import ConcurrentStatsTable
from lib.report_api._shared import get_response_data

if TYPE_CHECKING:
    from typing import Protocol

    class ConcurrentAPI(Protocol):
        def search_sessions(self, *, offset: int, limit: int, search_payload: dict) -> object: ...

        def search_connections(self, *, offset: int, limit: int, connection_params: dict) -> object: ...


logger = logging.getLogger(__name__)


@dataclass
class ConcurrentStatsSummary:
    sessions: int
    connections_total: int
    timestamp: str


def _fetch_session_count(api: ConcurrentAPI) -> int:
    """Fetch current concurrent PrivX user session count.

    Counts distinct users with active (non-logged-out) sessions,
    excluding API client sessions (domain=privx-external).
    """
    try:
        resp = api.search_sessions(offset=0, limit=1000, search_payload={})
        d = get_response_data(resp, "search_sessions")
        if d is None:
            return 0

        items = d.get("items", [])
        # Count distinct user_ids from active, non-API sessions
        active_users: set[str] = set()
        for session in items:
            if session.get("logged_out", False):
                continue
            domain = str(session.get("domain", "")).lower()
            if domain == "privx-external":
                continue
            user_id = session.get("user_id", "")
            if user_id:
                active_users.add(user_id)

        return len(active_users)
    except Exception as exc:
        logger.warning("concurrent_stats: failed to fetch sessions: %s", exc)
        return 0


def _fetch_connection_counts(api: ConcurrentAPI) -> dict[str, int]:
    """Fetch concurrent connection counts with breakdown by type and mode."""
    result = {
        "connections_total": 0,
        "connections_ssh": 0,
        "connections_rdp": 0,
        "connections_db": 0,
        "connections_web": 0,
        "connections_vnc": 0,
        "connections_net": 0,
        "connections_mode_ui": 0,
        "connections_mode_mitm": 0,
        "connections_mode_other": 0,
    }

    try:
        # Fetch active connections (status=CONNECTED)
        resp = api.search_connections(
            offset=0,
            limit=1000,
            connection_params={"status": ["CONNECTED"]},
        )
        d = get_response_data(resp, "search_connections")
        if d is None:
            return result

        items = d.get("items", [])
        result["connections_total"] = int(d.get("count", len(items)))

        for conn in items:
            conn_type = str(conn.get("type", "")).strip().upper()
            mode = str(conn.get("mode", "")).strip().upper()

            # Type breakdown
            if conn_type == "SSH":
                result["connections_ssh"] += 1
            elif conn_type == "RDP":
                result["connections_rdp"] += 1
            elif conn_type in ("DB", "DATABASE", "MYSQL", "POSTGRES", "MSSQL"):
                result["connections_db"] += 1
            elif conn_type in ("WEB", "HTTP", "HTTPS"):
                result["connections_web"] += 1
            elif conn_type == "VNC":
                result["connections_vnc"] += 1
            elif conn_type == "NET":
                result["connections_net"] += 1

            # Mode breakdown
            if mode in ("UI", "WEB", "BROWSER"):
                result["connections_mode_ui"] += 1
            elif mode in ("MITM", "TRANSPARENT"):
                result["connections_mode_mitm"] += 1
            else:
                result["connections_mode_other"] += 1

    except Exception as exc:
        logger.warning("concurrent_stats: failed to fetch connections: %s", exc)

    return result


def sync_concurrent_stats(api: ConcurrentAPI) -> ConcurrentStatsSummary:
    """Capture a single concurrent stats snapshot and store it."""
    now = datetime.now(UTC)
    # Truncate to the minute
    timestamp = now.replace(second=0, microsecond=0)

    sessions = _fetch_session_count(api)
    connections = _fetch_connection_counts(api)

    payload = {
        "sessions": sessions,
        **connections,
    }

    logger.info(
        "concurrent_stats: sessions=%d connections_total=%d (SSH=%d RDP=%d DB=%d WEB=%d VNC=%d NET=%d)",
        sessions,
        connections["connections_total"],
        connections["connections_ssh"],
        connections["connections_rdp"],
        connections["connections_db"],
        connections["connections_web"],
        connections["connections_vnc"],
        connections["connections_net"],
    )

    row = {"timestamp": timestamp, "data": payload}

    db = use_database("data")
    stmt = pg_insert(ConcurrentStatsTable).values([row])
    stmt = stmt.on_conflict_do_update(
        index_elements=[ConcurrentStatsTable.c.timestamp],
        set_={"data": stmt.excluded.data},
    )
    with db.connection.begin():
        db.connection.execute(stmt)

    return ConcurrentStatsSummary(
        sessions=sessions,
        connections_total=connections["connections_total"],
        timestamp=timestamp.isoformat(),
    )
