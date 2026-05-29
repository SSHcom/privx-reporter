"""Fetch directory source counts for the overview dashboard."""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from typing import Any, Protocol

from lib.report_api._shared import get_response_data
from streamlit.logger import get_logger
from ui.services.cache_service import get_cached_privx_client

logger = get_logger(__name__)

# Source types to skip (already shown elsewhere on the overview page)
_SKIP_TYPES = {"LOCAL", "LOCALHOST", "API-CLIENT"}

_MAX_PROCESSING_RETRIES = 2
_PROCESSING_WAIT_SECONDS = 3

# Patterns to extract counts from status_text
_USERS_RE = re.compile(r"(\d+)\s+(?:total\s+)?users")
_HOSTS_RE = re.compile(r"(\d+)\s+hosts")


class _SupportsGetSources(Protocol):
    def get_sources(self) -> object: ...


def _parse_counts(status_text: str) -> tuple[int | None, int | None]:
    """Extract user and host counts from status_text.

    Returns (users, hosts) where None means the field is not present.
    """
    text = status_text.lower()
    users: int | None = None
    hosts: int | None = None

    if "users" in text:
        m = _USERS_RE.search(text)
        if m:
            users = int(m.group(1))

    if "hosts" in text:
        m = _HOSTS_RE.search(text)
        if m:
            hosts = int(m.group(1))

    return users, hosts


def _fetch_sources(api: _SupportsGetSources) -> list[dict[str, Any]]:
    """Fetch sources, retrying if any are PROCESSING."""
    for attempt in range(_MAX_PROCESSING_RETRIES + 1):
        resp = api.get_sources()
        d = get_response_data(resp, "get_sources")
        if d is None:
            return []

        items = d.get("items", []) if isinstance(d, dict) else (d if isinstance(d, list) else [])

        has_processing = any(
            item.get("status_code") == "PROCESSING"
            for item in items
            if isinstance(item, dict)
            and item.get("connection", {}).get("type", "") not in _SKIP_TYPES
            and item.get("status_code") != "DISABLED"
        )

        if not has_processing or attempt == _MAX_PROCESSING_RETRIES:
            return items

        logger.info(
            "overview_directories: some sources still PROCESSING, retrying in %ds (attempt %d/%d)",
            _PROCESSING_WAIT_SECONDS,
            attempt + 1,
            _MAX_PROCESSING_RETRIES,
        )
        time.sleep(_PROCESSING_WAIT_SECONDS)

    return items


def fetch_data() -> dict[str, Any]:
    """Return directory source entries with parsed user/host counts."""
    base: dict[str, Any] = {
        "directories": [],
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    try:
        api = get_cached_privx_client()
    except SystemExit as exc:
        return {**base, "error": f"Cannot connect to PrivX. Check connectivity and PRIVX_HOSTNAME. ({exc})"}
    except Exception as exc:
        return {**base, "error": f"Failed to connect to PrivX: {exc}"}

    try:
        items = _fetch_sources(api)
    except SystemExit as exc:
        return {**base, "error": f"Cannot connect to PrivX. Check connectivity and PRIVX_HOSTNAME. ({exc})"}
    except Exception as exc:
        return {**base, "error": f"Failed to fetch sources: {exc}"}

    logger.info("overview_directories: fetched %d sources", len(items))

    directories: list[dict[str, Any]] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        name = item.get("name", "Unknown")
        status_code = item.get("status_code", "")
        conn_type = (item.get("connection") or {}).get("type", "")
        status_text = item.get("status_text", "")

        if status_code == "DISABLED":
            logger.debug("overview_directories: skipping %s (DISABLED)", name)
            continue

        if conn_type in _SKIP_TYPES:
            logger.debug("overview_directories: skipping %s (type=%s)", name, conn_type)
            continue

        text_lower = status_text.lower()

        # Only include if status_text mentions users or hosts
        if "users" not in text_lower and "hosts" not in text_lower:
            logger.debug("overview_directories: skipping %s (no users/hosts in status_text=%r)", name, status_text)
            continue

        users, hosts = _parse_counts(status_text)
        processing = status_code == "PROCESSING"

        logger.info(
            "overview_directories: including %s type=%s users=%s hosts=%s processing=%s",
            name,
            conn_type,
            users,
            hosts,
            processing,
        )

        directories.append(
            {
                "name": name,
                "type": conn_type,
                "users": users,
                "hosts": hosts,
                "processing": processing,
            }
        )

    logger.info("overview_directories: total directories=%d", len(directories))

    return {
        "directories": directories,
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
