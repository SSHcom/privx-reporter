"""Filesystem caching utilities for report data."""

import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lib.env import EnvConfig
from lib.report_api.access_group import get_access_group_by_id

# Max age of access group cache (name/comment can change)
CACHE_MAX_AGE_SECONDS = 3600  # 1 hour

if TYPE_CHECKING:
    import privx_api


logger = logging.getLogger(__name__)


def _get_cache_dir() -> Path:
    """Get the cache directory path."""
    report_dir = Path(EnvConfig.get_report_out_dir())
    cache_dir = report_dir / ".tmp" / "access_groups"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_cached_access_group(access_group_id: str) -> dict[str, Any] | None:
    """
    Get access group from filesystem cache.

    Args:
        access_group_id: Access group ID to retrieve from cache

    Returns:
        dict | None: Cached access group data or None if not found
    """
    cache_file = _get_cache_dir() / f"{access_group_id}.json"

    if cache_file.exists():
        try:
            age_seconds = time.time() - cache_file.stat().st_mtime
            if age_seconds > CACHE_MAX_AGE_SECONDS:
                cache_file.unlink()
                logger.debug(f"Discarded stale cache for {access_group_id} (age {age_seconds:.0f}s)")
                return None
            with open(cache_file) as f:
                data: dict[str, Any] = json.load(f)
                return data
        except Exception as e:
            logger.warning(f"Failed to read cache for {access_group_id}: {e}")

    return None


def _cache_access_group(access_group_id: str, data: dict[str, Any]) -> None:
    """
    Cache access group data to filesystem.

    Args:
        access_group_id: Access group ID to cache
        data: Access group data to store
    """
    cache_file = _get_cache_dir() / f"{access_group_id}.json"

    try:
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to cache {access_group_id}: {e}")


def fetch_access_group_details_cached(api: "privx_api.PrivXAPI", access_group_id: str) -> dict[str, Any]:
    """
    Fetch access group details with filesystem caching.

    Returns dict with: access_group_name, access_group_comment, access_group_default

    Args:
        api: PrivX API client instance
        access_group_id: Access group ID to fetch

    Returns:
        dict: Access group details with keys: access_group_name, access_group_comment, access_group_default
    """
    if not access_group_id:
        return {
            "access_group_name": "",
            "access_group_comment": "",
            "access_group_default": False,
        }

    # Try cache first
    cached = _get_cached_access_group(access_group_id)
    if cached:
        logger.debug(f"Access group {access_group_id} loaded from cache")
        return cached

    # Fetch from API
    access_group = get_access_group_by_id(api, access_group_id)

    if access_group:
        result = {
            "access_group_name": access_group.get("name", ""),
            "access_group_comment": access_group.get("comment", ""),
            "access_group_default": access_group.get("default", False),
        }

        # Cache it
        _cache_access_group(access_group_id, result)

        return result

    return {
        "access_group_name": "",
        "access_group_comment": "",
        "access_group_default": False,
    }
