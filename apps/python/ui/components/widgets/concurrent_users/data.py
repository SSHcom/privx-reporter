from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from lib import report_api
from streamlit.logger import get_logger
from ui.services.cache_service import get_cached_privx_client

logger = get_logger(__name__)


def _normalize_protocol(raw_type: object) -> str:
    value = str(raw_type or "").strip().upper()
    if value == "SSH":
        return "SSH"
    if value == "RDP":
        return "RDP"
    if value in {"WEB", "HTTP", "HTTPS", "BROWSER"}:
        return "Web"
    if value == "VNC":
        return "VNC"
    if value in {"DB", "DATABASE", "MYSQL", "POSTGRES", "POSTGRESQL", "MSSQL", "MONGODB"}:
        return "DB"
    return "Other"


def _resolve_network_target_identity(connection: dict[str, Any]) -> tuple[str, str]:
    target_network = connection.get("target_network") or {}
    target_network_data = connection.get("target_network_data") or {}
    target_host = connection.get("target_host") or {}
    target_host_data = connection.get("target_host_data") or {}

    network_id = str(target_network.get("id", "")).strip() or str(target_network_data.get("id", "")).strip()
    host_id = str(target_host.get("id", "")).strip() or str(target_host_data.get("id", "")).strip()
    network_name = str(target_network_data.get("name", "")).strip()
    host_common_name = str(target_host.get("common_name", "")).strip()
    host_data_common_name = str(target_host_data.get("common_name", "")).strip()
    target_address = str(connection.get("target_host_address", "")).strip()
    display_name = network_name or host_common_name or host_data_common_name or target_address or "Unknown"
    stable_key = network_id or host_id or target_address or display_name
    return stable_key, display_name


def _normalize_file_transfer_type(connection: dict[str, Any]) -> str | None:
    connection_type = str(connection.get("type", "")).strip().upper()
    if connection_type in {"SFTP", "SCP"}:
        return connection_type
    if connection_type in {"FILE_TRANSFER", "FILE-TRANSFER", "FILETRANSFER"}:
        return "FILE_TRANSFER"

    target_host_data = connection.get("target_host_data") or {}
    services = target_host_data.get("services", []) or []
    for service in services:
        service_name = str((service or {}).get("service", "")).strip().upper()
        if service_name in {"SFTP", "SCP"}:
            return service_name

    return None


def _normalize_client_method(connection: dict[str, Any]) -> str:
    mode = str(connection.get("mode", "")).strip().upper()
    connection_type = str(connection.get("type", "")).strip().upper()
    user_agent = str(connection.get("user_agent", "")).strip().lower()
    target_api_data = connection.get("target_api_data") or {}

    if mode == "API" or connection_type == "API" or str(target_api_data.get("id", "")).strip():
        return "API"
    if mode in {"WEB", "BROWSER", "UI"} or connection_type in {"WEB", "HTTP", "HTTPS"}:
        return "Web"
    if "mozilla/" in user_agent or "chrome/" in user_agent or "safari/" in user_agent:
        return "Web"
    return "Native Client"


def _resolve_target_account(connection: dict[str, Any]) -> str:
    target_account = str(connection.get("target_host_account", "")).strip()
    if target_account:
        return target_account

    target_host_data = connection.get("target_host_data") or {}
    accounts = target_host_data.get("accounts", []) or []
    if isinstance(accounts, list):
        for account in accounts:
            account_name = str((account or {}).get("name", "")).strip()
            if account_name:
                return account_name

    return "Unknown"


def fetch_data(batch_size: int = 100) -> dict[str, Any]:
    """Fetch active connections and aggregate concurrent-user metrics."""
    started_at = time.perf_counter()
    try:
        api = get_cached_privx_client()
    except Exception as exc:
        result = {
            "label": "Concurrent PrivX Users",
            "description": "Live active sessions and unique users from PrivX connections with status CONNECTED.",
            "active_sessions": 0,
            "concurrent_users": 0,
            "protocol_counts": {"RDP": 0, "SSH": 0, "Web": 0, "DB": 0, "VNC": 0, "Other": 0},
            "concurrent_network_targets": 0,
            "top_network_targets": [],
            "concurrent_file_transfer_sessions": 0,
            "file_transfer_type_counts": {"SFTP": 0, "SCP": 0, "FILE_TRANSFER": 0},
            "client_method_counts": {"Native Client": 0, "Web": 0, "API": 0},
            "top_users": [],
            "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "error": f"Failed to authenticate PrivX client: {exc}",
        }
        logger.info("concurrent_users.fetch_data took %.2fs", time.perf_counter() - started_at)
        return result

    offset = 0
    active_connections: list[dict[str, Any]] = []

    while True:
        try:
            response = report_api.search_connections(
                api,
                offset=offset,
                limit=batch_size,
                search_payload={"status": ["CONNECTED"]},
            )
        except Exception as exc:
            result = {
                "label": "Concurrent PrivX Users",
                "description": "Live active sessions and unique users from PrivX connections with status CONNECTED.",
                "active_sessions": 0,
                "concurrent_users": 0,
                "protocol_counts": {"RDP": 0, "SSH": 0, "Web": 0, "DB": 0, "VNC": 0, "Other": 0},
                "concurrent_network_targets": 0,
                "top_network_targets": [],
                "concurrent_file_transfer_sessions": 0,
                "file_transfer_type_counts": {"SFTP": 0, "SCP": 0, "FILE_TRANSFER": 0},
                "client_method_counts": {"Native Client": 0, "Web": 0, "API": 0},
                "top_users": [],
                "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "error": f"Failed to query active connections: {exc}",
            }
            logger.info("concurrent_users.fetch_data took %.2fs", time.perf_counter() - started_at)
            return result

        items = list(response.get("items", []))
        if not items:
            break

        active_connections.extend(items)

        total_count = int(response.get("count", 0) or 0)
        if len(active_connections) >= total_count:
            break

        offset += batch_size

    users: dict[str, int] = {}
    protocols = {"RDP": 0, "SSH": 0, "Web": 0, "DB": 0, "VNC": 0, "Other": 0}
    network_targets: dict[str, int] = {}
    network_target_names: dict[str, str] = {}
    file_transfer_types = {"SFTP": 0, "SCP": 0, "FILE_TRANSFER": 0}
    client_method_counts = {"Native Client": 0, "Web": 0, "API": 0}
    timeline_counts: dict[str, int] = {}
    timeline_users: dict[str, set[str]] = {}
    timeline_protocols: dict[str, dict[str, int]] = {}
    timeline_accounts: dict[str, dict[str, int]] = {}
    file_transfer_sessions = 0
    for connection in active_connections:
        user_data = connection.get("user_data") or {}
        user_obj = connection.get("user") or {}

        email = str(user_data.get("email", "")).strip()
        principal = str(user_data.get("principal", "")).strip()
        display_name = str(user_obj.get("display_name", "")).strip()
        user_id = str(user_obj.get("id", "")).strip()

        user_key = email or principal or display_name or user_id or "Unknown"
        users[user_key] = users.get(user_key, 0) + 1

        protocol = _normalize_protocol(connection.get("type"))
        protocols[protocol] = protocols.get(protocol, 0) + 1

        target_key, target_name = _resolve_network_target_identity(connection)
        network_targets[target_key] = network_targets.get(target_key, 0) + 1
        if target_key not in network_target_names:
            network_target_names[target_key] = target_name

        file_transfer_type = _normalize_file_transfer_type(connection)
        if file_transfer_type is not None:
            file_transfer_sessions += 1
            file_transfer_types[file_transfer_type] = file_transfer_types.get(file_transfer_type, 0) + 1

        client_method = _normalize_client_method(connection)
        client_method_counts[client_method] = client_method_counts.get(client_method, 0) + 1
        target_account = _resolve_target_account(connection)

        connected_raw = connection.get("connected")
        if connected_raw:
            connected_str = str(connected_raw).strip()
            if connected_str:
                minute_bucket = connected_str[:16]
                timeline_counts[minute_bucket] = timeline_counts.get(minute_bucket, 0) + 1
                if minute_bucket not in timeline_users:
                    timeline_users[minute_bucket] = set()
                timeline_users[minute_bucket].add(user_key)
                if minute_bucket not in timeline_protocols:
                    timeline_protocols[minute_bucket] = {}
                protocol_bucket = timeline_protocols[minute_bucket]
                protocol_bucket[protocol] = protocol_bucket.get(protocol, 0) + 1
                if minute_bucket not in timeline_accounts:
                    timeline_accounts[minute_bucket] = {}
                account_bucket = timeline_accounts[minute_bucket]
                account_bucket[target_account] = account_bucket.get(target_account, 0) + 1

    sorted_users = sorted(users.items(), key=lambda item: (-item[1], item[0].lower()))
    sorted_targets = sorted(network_targets.items(), key=lambda item: (-item[1], item[0].lower()))
    sorted_timeline = sorted(timeline_counts.items(), key=lambda item: item[0])

    result = {
        "label": "Concurrent PrivX Users",
        "description": "Live active sessions and unique users from PrivX connections with status CONNECTED.",
        "active_sessions": len(active_connections),
        "concurrent_users": len(users),
        "protocol_counts": protocols,
        "top_users": [{"User": user, "Sessions": count} for user, count in sorted_users[:10]],
        "session_timeline": [
            {
                "Time": time_bucket,
                "Sessions": count,
                "Users": ", ".join(sorted(timeline_users.get(time_bucket, set()))[:10]),
                "Protocol": ", ".join(
                    proto
                    for proto, _proto_count in sorted(
                        timeline_protocols.get(time_bucket, {}).items(),
                        key=lambda item: (-item[1], item[0]),
                    )
                ),
                "Target Account": ", ".join(
                    f"{account}"
                    for account, account_count in sorted(
                        timeline_accounts.get(time_bucket, {}).items(),
                        key=lambda item: (-item[1], item[0]),
                    )
                ),
            }
            for time_bucket, count in sorted_timeline
        ],
        "concurrent_network_targets": len(network_targets),
        "top_network_targets": [
            {
                "Network Target": network_target_names.get(target_key, target_key),
                "Target Key": target_key,
                "Sessions": count,
            }
            for target_key, count in sorted_targets[:10]
        ],
        "concurrent_file_transfer_sessions": file_transfer_sessions,
        "file_transfer_type_counts": file_transfer_types,
        "client_method_counts": client_method_counts,
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
    logger.info("concurrent_users.fetch_data took %.2fs", time.perf_counter() - started_at)
    return result
