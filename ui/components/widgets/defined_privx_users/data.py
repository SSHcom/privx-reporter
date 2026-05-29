from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from lib import report_api
from streamlit.logger import get_logger
from ui.services.cache_service import get_cached_privx_client

logger = get_logger(__name__)

MAX_USERS_DISPLAY = 100


def _normalize_source_type(user: dict[str, Any]) -> str:
    source_type = str(user.get("source_type", "")).strip()
    return source_type if source_type else "Unknown"


def _resolve_display_name(user: dict[str, Any]) -> str:
    return (
        str(user.get("name", "")).strip()
        or str(user.get("username", "")).strip()
        or str(user.get("principal", "")).strip()
        or str(user.get("email", "")).strip()
        or str(user.get("id", "")).strip()
        or "Unknown"
    )


def _resolve_directory(user: dict[str, Any]) -> str:
    source = user.get("source") if isinstance(user.get("source"), dict) else {}
    return (
        str(user.get("source_name", "")).strip()
        or str(user.get("directory", "")).strip()
        or str(user.get("directory_name", "")).strip()
        or str(source.get("name", "")).strip()
        or "-"
    )


def fetch_data() -> dict[str, Any]:
    """Fetch total defined PrivX users."""
    started_at = time.perf_counter()
    base_result: dict[str, Any] = {
        "label": "Total Defined PrivX User",
        "description": "Live total count of users defined in PrivX.",
        "total_defined_privx_users": 0,
        "local_users": 0,
        "non_local_users": 0,
        "users": [],
        "users_shown": 0,
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    try:
        api = get_cached_privx_client()
    except Exception as exc:
        result = {
            **base_result,
            "error": f"Failed to authenticate PrivX client: {exc}",
        }
        logger.info("defined_privx_users.fetch_data took %.2fs", time.perf_counter() - started_at)
        return result

    try:
        users = report_api.users.get_all_users(api)
    except Exception as exc:
        result = {
            **base_result,
            "error": f"Failed to query PrivX users: {exc}",
        }
        logger.info("defined_privx_users.fetch_data took %.2fs", time.perf_counter() - started_at)
        return result

    local_users = 0
    user_rows: list[dict[str, str]] = []
    logger.info("Fetched %d users from API", len(users))

    for index, user in enumerate(users):
        source_type = _normalize_source_type(user)
        source_type_upper = source_type.upper()
        if source_type_upper == "LOCAL":
            local_users += 1

        if index < MAX_USERS_DISPLAY:
            user_rows.append(
                {
                    # "Name": _resolve_display_name(user),
                    "Username": str(user.get("username", "")).strip(),
                    # "Principal": str(user.get("principal", "")).strip(),
                    "Email": str(user.get("email", "")).strip(),
                    # "Directory": _resolve_directory(user),
                    # "Authentication Method": str(user.get("authentication_method", "")).strip() or "-",
                    # "Login Method": str(user.get("login_method", "")).strip() or "-",
                }
            )

    total_users = len(users)

    result = {
        **base_result,
        "total_defined_privx_users": total_users,
        "local_users": local_users,
        "non_local_users": max(0, total_users - local_users),
        "users": user_rows,
        "users_shown": len(user_rows),
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
    logger.info("defined_privx_users.fetch_data took %.2fs", time.perf_counter() - started_at)
    return result
