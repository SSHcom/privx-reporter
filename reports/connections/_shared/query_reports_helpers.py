"""Shared helpers for query-based connections reports (query and query-db)."""

from typing import Any

from reports.connections._shared import extract_target_ips


def extract_connection_fields(connection: dict[str, Any]) -> dict[str, Any]:
    """
    Extract and format connection fields for output.

    Args:
        connection: Raw connection data dict (from API or DB JSONB column)

    Returns:
        Dictionary with formatted connection fields
    """
    user_data = connection.get("user_data", {})
    user_name = user_data.get("full_name") or user_data.get("principal") or ""
    user_id = connection.get("user", {}).get("id", "")

    authorized_endpoints_list = connection.get("target_api_data", {}).get("authorized_endpoints") or []
    endpoints_joined = ", ".join(
        endpoint.get("host", "") for endpoint in authorized_endpoints_list if endpoint.get("host")
    )
    authorized_endpoints = f'"{endpoints_joined}"' if "," in endpoints_joined else endpoints_joined

    dst_list = connection.get("target_network_data", {}).get("dst")
    target_ips = extract_target_ips(dst_list)

    return {
        "connection_id": connection.get("id", ""),
        "created": connection.get("created", ""),
        "connected": connection.get("connected", ""),
        "disconnected": connection.get("disconnected", ""),
        "duration": connection.get("duration", ""),
        "status": connection.get("status", ""),
        "type": connection.get("type", ""),
        "authorized_endpoints": authorized_endpoints,
        "user_id": user_id,
        "user_name": user_name,
        "target_host_id": connection.get("target_host", {}).get("id", ""),
        "target_host_address": connection.get("target_host_address", ""),
        "target_host_common_name": connection.get("target_host", {}).get("common_name", ""),
        "target_host_account": connection.get("target_host_account", ""),
        "target_ips": target_ips,
    }
