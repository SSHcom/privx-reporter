from __future__ import annotations

from typing import Any


def user_key(connection: dict[str, Any]) -> str:
    user_data = connection.get("user_data") or {}
    user_obj = connection.get("user") or {}

    email = str(user_data.get("email", "")).strip()
    full_name = str(user_data.get("full_name", "")).strip()
    principal = str(user_data.get("principal", "")).strip()
    display_name = str(user_obj.get("display_name", "")).strip()
    user_id = str(user_obj.get("id", "")).strip()

    return email or full_name or principal or display_name or user_id or "Unknown"


def is_api_connection(connection: dict[str, Any]) -> bool:
    mode = str(connection.get("mode", "")).strip().upper()
    conn_type = str(connection.get("type", "")).strip().upper()
    user_agent = str(connection.get("user_agent", "")).strip().lower()
    target_api_data = connection.get("target_api_data") or {}

    if mode == "API" or conn_type == "API":
        return True
    if str(target_api_data.get("id", "")).strip():
        return True
    return "api" in user_agent and "mozilla" not in user_agent


def target_account_key(connection: dict[str, Any]) -> str:
    target_account = str(connection.get("target_host_account", "")).strip()
    if target_account:
        return target_account

    host_data = connection.get("target_host_data") or {}
    unix_account = str(host_data.get("unix_account", "")).strip()
    windows_account = str(host_data.get("windows_account", "")).strip()

    return unix_account or windows_account or "Unknown"


def target_host_identity(connection: dict[str, Any]) -> tuple[str, str, str]:
    host_data = connection.get("target_host_data") or {}
    host_obj = connection.get("target_host") or {}

    host_name = (
        str(connection.get("target_host_name", "")).strip()
        or str(host_obj.get("common_name", "")).strip()
        or str(host_obj.get("name", "")).strip()
        or str(host_data.get("common_name", "")).strip()
        or str(host_data.get("host_name", "")).strip()
        or str(host_data.get("hostname", "")).strip()
        or "Unknown"
    )
    host_address = (
        str(connection.get("target_host_address", "")).strip()
        or str(host_obj.get("address", "")).strip()
        or str(host_data.get("address", "")).strip()
        or "-"
    )
    host_uuid = str(host_obj.get("id", "")).strip() or str(host_data.get("id", "")).strip() or "-"

    return host_name, host_address, host_uuid


def iter_nested_values(payload: object) -> list[tuple[str, object]]:
    values: list[tuple[str, object]] = []

    def _walk(node: object, path: str = "") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                current = f"{path}.{key}" if path else str(key)
                values.append((current, value))
                _walk(value, current)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                current = f"{path}[{index}]" if path else f"[{index}]"
                values.append((current, item))
                _walk(item, current)

    _walk(payload)
    return values


def resolve_ueba_label(connection: dict[str, Any]) -> str | None:
    nested = iter_nested_values(connection)

    usual_terms = {"usual", "normal", "benign"}
    anomaly_terms = {"anomaly", "anomalous", "abnormal", "suspicious", "risk"}

    for path, value in nested:
        path_lower = path.lower()

        if isinstance(value, bool):
            if value and ("anomaly" in path_lower or "suspicious" in path_lower):
                return "anomaly"
            if value and ("usual" in path_lower or "normal" in path_lower):
                return "usual"
            continue

        value_str = str(value).strip().lower()
        if not value_str:
            continue

        if any(token in path_lower for token in ("ueba", "risk", "anomaly", "classification", "behavior")):
            if value_str in anomaly_terms:
                return "anomaly"
            if value_str in usual_terms:
                return "usual"

    return None
