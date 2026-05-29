"""Fetch total counts for the overview dashboard."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lib import report_api
from lib.clients.postgresql import use_database
from lib.database.models.sync.system_trend import SystemTrendTable
from lib.report_api._shared import get_response_data
from streamlit.logger import get_logger
from ui.services.cache_service import get_cached_privx_client

logger = get_logger(__name__)

_ALL_METRIC_KEYS = [
    "roles",
    "local_users",
    "hosts",
    "network_targets",
    "api_targets",
    "access_groups",
    "workflows",
    "secrets",
    "sources",
    "api_clients",
    "hosts_ssh",
    "hosts_rdp",
    "hosts_vnc",
    "hosts_web",
    "hosts_db",
]


class PrivXUnavailableError(RuntimeError):
    """Raised when a PrivX API call aborts due to connection/auth errors."""


def _safe_count(label: str, fn: object) -> int:
    """Call *fn* and return the integer result, logging on failure."""
    try:
        result = fn()  # type: ignore[operator]
        return int(result)
    except SystemExit as exc:
        raise PrivXUnavailableError(f"PrivX call failed during {label}") from exc
    except Exception as exc:
        logger.warning("overview_counts: failed to fetch %s: %s", label, exc)
        return 0


def fetch_data() -> dict[str, Any]:
    """Return total counts for key PrivX entities."""
    base: dict[str, Any] = {
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
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    try:
        api = get_cached_privx_client()
    except Exception as exc:
        return {**base, "error": f"Failed to connect to PrivX: {exc}"}

    # Roles — search with limit=1 to get count only
    def _roles() -> int:
        data = report_api.roles.search_roles(api, search_payload={}, offset=0, limit=1)
        return int((data or {}).get("count", 0))

    # Local users — get_users returns {count, items}
    def _local_users() -> int:
        data = report_api.users.get_users(api, offset=0, limit=1)
        return int((data or {}).get("count", 0))

    # Hosts
    def _hosts() -> int:
        data = report_api.hosts.search_hosts(api, search_payload={}, offset=0, limit=1)
        return int((data or {}).get("count", 0))

    # Network targets
    def _network_targets() -> int:
        resp = api.get_network_targets(offset=0, limit=1)
        d = get_response_data(resp, "get_network_targets")
        return int((d or {}).get("count", 0))

    # API targets
    def _api_targets() -> int:
        resp = api.get_api_targets(offset=0, limit=1)
        d = get_response_data(resp, "get_api_targets")
        return int((d or {}).get("count", 0))

    # Access groups
    def _access_groups() -> int:
        data = report_api.search_access_groups(api, offset=0, limit=1)
        return int((data or {}).get("count", 0))

    # Workflows
    def _workflows() -> int:
        resp = api.get_workflows(offset=0, limit=1)
        d = get_response_data(resp, "get_workflows")
        return int((d or {}).get("count", 0))

    # Secrets
    def _secrets() -> int:
        data = report_api.search_secrets(api, offset=0, limit=1)
        return int((data or {}).get("count", 0))

    # Sources/Directories — returns full list, count the items
    def _sources() -> int:
        resp = api.get_sources()
        d = get_response_data(resp, "get_sources")
        if d is None:
            return 0
        items = d.get("items", d) if isinstance(d, dict) else d
        return len(items) if isinstance(items, list) else int(d.get("count", 0))

    # API Clients — returns full list, count the items
    def _api_clients() -> int:
        resp = api.get_api_clients()
        d = get_response_data(resp, "get_api_clients")
        if d is None:
            return 0
        items = d.get("items", d) if isinstance(d, dict) else d
        return len(items) if isinstance(items, list) else int(d.get("count", 0))

    # Host counts by service type
    def _hosts_by_service(service: str) -> int:
        data = report_api.hosts.search_hosts(api, search_payload={"service": [service]}, offset=0, limit=1)
        return int((data or {}).get("count", 0))

    def _system_trend_points() -> list[dict[str, Any]]:
        db = use_database("data")
        with db.engine.connect() as sql_connection:
            rows = (
                sql_connection.execute(
                    SystemTrendTable.select().order_by(SystemTrendTable.c.timestamp.desc()).limit(90)
                )
                .mappings()
                .all()
            )

        trend: list[dict[str, Any]] = []
        for row in reversed(rows):
            ts = row.get("timestamp")
            payload = row.get("data")
            if ts is None or not isinstance(payload, dict):
                continue

            point: dict[str, Any] = {"timestamp": ts.strftime("%Y-%m-%d")}
            for key in _ALL_METRIC_KEYS:
                try:
                    point[key] = int(payload.get(key, 0))
                except (TypeError, ValueError):
                    point[key] = 0

            trend.append(point)
        return trend

    def _safe_system_trend_points() -> list[dict[str, Any]]:
        try:
            return _system_trend_points()
        except Exception as exc:
            logger.warning("overview_counts: failed to fetch system_trend: %s", exc)
            return []

    trend_points = _safe_system_trend_points()

    # Build per-metric trend lists from the full trend points
    metric_trends: dict[str, list[dict[str, Any]]] = {}
    for key in _ALL_METRIC_KEYS:
        metric_trends[f"{key}_trend"] = [{"timestamp": p["timestamp"], key: p.get(key, 0)} for p in trend_points]

    try:
        return {
            "roles": _safe_count("roles", _roles),
            "local_users": _safe_count("local_users", _local_users),
            "hosts": _safe_count("hosts", _hosts),
            "network_targets": _safe_count("network_targets", _network_targets),
            "api_targets": _safe_count("api_targets", _api_targets),
            "access_groups": _safe_count("access_groups", _access_groups),
            "workflows": _safe_count("workflows", _workflows),
            "secrets": _safe_count("secrets", _secrets),
            "sources": _safe_count("sources", _sources),
            "api_clients": _safe_count("api_clients", _api_clients),
            "hosts_ssh": _safe_count("hosts_ssh", lambda: _hosts_by_service("SSH")),
            "hosts_rdp": _safe_count("hosts_rdp", lambda: _hosts_by_service("RDP")),
            "hosts_vnc": _safe_count("hosts_vnc", lambda: _hosts_by_service("VNC")),
            "hosts_web": _safe_count("hosts_web", lambda: _hosts_by_service("WEB")),
            "hosts_db": _safe_count("hosts_db", lambda: _hosts_by_service("DB")),
            **metric_trends,
            "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }
    except PrivXUnavailableError as exc:
        logger.warning("overview_counts: %s", exc)
        return {**base, **metric_trends, "error": "Cannot connect to PrivX. Check connectivity and PRIVX_HOSTNAME."}
