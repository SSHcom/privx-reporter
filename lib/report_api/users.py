"""Module for PrivX Users API operations."""

import logging
from typing import Any

import privx_api
import privx_api.exceptions

from lib.clients.privx.http_error import handle_http_5xx_error
from lib.report_api._shared import get_response_data

logger = logging.getLogger(__name__)


def get_user_by_id(api: privx_api.PrivXAPI, id: str) -> dict[Any, Any] | None:
    """
    Get a user by id.

    Returns:
        dict | None: User dictionary with all fields, or None if not found
    """

    try:
        response = api.get_user(id)

    except privx_api.exceptions.InternalAPIException as e:
        handle_http_5xx_error(e, f"get_user_by_id for id={id}")

    data = get_response_data(response, "get_user_by_id")
    if data is None:
        return None
    result: dict[Any, Any] = data
    return result


def get_users(api: privx_api.PrivXAPI, offset: int = 0, limit: int | None = None) -> dict[Any, Any] | None:
    """
    Get all users.

    Args:
        api: PrivX API client instance
        offset: Offset for pagination (default: 0)
        limit: Maximum number of items to return (default: None = 100 for all)

    Returns:
        dict | None: User dictionary with all fields, or None if not found
    """

    try:
        if limit is None:
            # Get all records with default pagination
            response = api.get_users(offset=offset, limit=100)
        else:
            # Paginated request
            response = api.get_users(offset=offset, limit=limit)
    except privx_api.exceptions.InternalAPIException as e:
        handle_http_5xx_error(e, f"get_users for offset={offset} and limit={limit}")

    data = get_response_data(response, "get_users")
    if data is None:
        return None
    result: dict[Any, Any] = data
    return result


def search_users(
    api: privx_api.PrivXAPI,
    search_payload: dict[Any, Any],
) -> dict[Any, Any] | None:
    """
    Search users from PrivX API.

    Args:
        api: PrivX API client instance
        search_payload: Search payload dictionary (e.g., {"keywords": "user_name"})

    Returns:
        dict | None: Response data containing users information with 'items' and 'count' keys.
    """
    try:
        response = api.search_users(search_payload=search_payload)
    except privx_api.exceptions.InternalAPIException as e:
        handle_http_5xx_error(e, "search_users")

    data = get_response_data(response, "search_users")

    if data is None:
        return None
    result: dict[Any, Any] = data
    return result


def get_all_users(api: privx_api.PrivXAPI) -> list[dict[Any, Any]]:
    """
    Get all users with automatic pagination.

    Args:
        api: PrivX API client instance

    Returns:
        list: List of all user dictionaries
    """
    all_items: list[dict[Any, Any]] = []
    offset = 0
    limit = 1000

    while True:
        try:
            response = api.get_users(offset=offset, limit=limit)
        except privx_api.exceptions.InternalAPIException as e:
            handle_http_5xx_error(e, f"get_users for offset={offset}")

        data = get_response_data(response, "get_users")
        if data is None:
            break

        items = list(data.get("items", []))
        total_count = int(data.get("count", 0) or 0)

        if not items:
            break

        all_items.extend(items)

        logger.info(f"Fetched {len(items)} users (offset={offset}, total so far={len(all_items)})")

        # If we've fetched all items based on count
        if total_count > 0 and len(all_items) >= total_count:
            break

        # Advance by actual returned size; server-side page size caps may ignore requested limit.
        offset += len(items)

    logger.info(f"Total users fetched: {len(all_items)}")
    return all_items
