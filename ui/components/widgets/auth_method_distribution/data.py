from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lib import report_api
from ui.services.cache_service import get_cached_privx_client


def _normalize_auth_method(user: dict[str, Any]) -> str:
    source_type = str(user.get("source_type", "")).strip().upper()
    auth_method = str(user.get("authentication_method", "")).strip().upper()
    login_method = str(user.get("login_method", "")).strip().upper()
    principal = str(user.get("principal", "")).strip().upper()
    username = str(user.get("username", "")).strip().upper()
    unix_account = str(user.get("unix_account", "")).strip().upper()
    windows_account = str(user.get("windows_account", "")).strip().upper()

    if "OIDC" in auth_method or "OIDC" in login_method or source_type == "OIDC":
        return "OIDC"
    if "SAML" in auth_method or "SAML" in login_method or source_type == "SAML":
        return "OIDC"
    if "CERT" in auth_method or "KEY" in auth_method or "SSH-KEY" in auth_method:
        return "Key"
    if source_type in {"LDAP", "AD", "ACTIVE_DIRECTORY", "DIRECTORY", "LOCAL"}:
        return "Password"
    if principal.startswith("ssh-") or username.startswith("ssh-"):
        return "Key"
    if unix_account or windows_account:
        return "Password"
    if not (source_type or auth_method or login_method):
        return "Unknown"
    return "Other"


def fetch_data() -> dict[str, Any]:
    """Fetch distribution of PrivX user authentication methods."""
    base_result = {
        "label": "Distribution of PrivX User Authentication Method",
        "description": "Live distribution for Password, OIDC, Key and Other methods.",
        "counts": {"Password": 0, "OIDC": 0, "Key": 0, "Other": 0},
        "total_users": 0,
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    try:
        api = get_cached_privx_client()
    except Exception as exc:
        return {
            **base_result,
            "error": f"Failed to authenticate PrivX client: {exc}",
        }

    try:
        users = report_api.users.get_all_users(api)
    except Exception as exc:
        return {
            **base_result,
            "error": f"Failed to query PrivX users: {exc}",
        }

    counts: dict[str, int] = {"Password": 0, "OIDC": 0, "Key": 0, "Other": 0}
    for user in users:
        method = _normalize_auth_method(user)
        counts[method] = counts.get(method, 0) + 1

    return {
        **base_result,
        "counts": counts,
        "total_users": len(users),
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
