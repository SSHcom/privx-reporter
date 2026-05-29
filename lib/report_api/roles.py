"""Module for PrivX Roles API operations."""

import logging
from typing import Any

import privx_api
import privx_api.exceptions

from lib.clients.privx.http_error import handle_http_5xx_error
from lib.report_api._shared import get_response_data

logger = logging.getLogger(__name__)


def get_role_by_name(api: privx_api.PrivXAPI, role_name: str) -> dict[Any, Any] | None:
    """
    Get a role by name.

    Returns:
        dict | None: Role dictionary with all fields, or None if not found
    """
    all_roles = get_roles(api)

    if not all_roles:
        logger.warning("No roles found or error fetching roles")
        return None

    # Find the role by name
    for role in all_roles:
        if role.get("name") == role_name:
            return role

    logger.error(f"Role '{role_name}' not found")
    return None


def get_role_by_id(api: privx_api.PrivXAPI, role_id: str) -> dict[Any, Any] | None:
    """
    Get a role by ID.

    Returns:
        dict | None: Role dictionary with all fields, or None if not found
    """
    try:
        response = api.get_role(role_id)
    except privx_api.exceptions.InternalAPIException as e:
        handle_http_5xx_error(e, f"get_role_by_id for role_id={role_id}")

    data = get_response_data(response, "get_role_by_id")
    if data is None:
        return None
    result: dict[Any, Any] = data
    return result


def get_roles(api: privx_api.PrivXAPI) -> list[dict[Any, Any]]:
    """
    Fetch all roles from PrivX API.

    Returns:
        dict: Response data containing roles information with 'items' key.
    """
    try:
        response = api.get_roles()
    except privx_api.exceptions.InternalAPIException as e:
        handle_http_5xx_error(e, "get_roles")

    data = get_response_data(response, "get_roles")

    if not data or data.get("count") is None or data.get("items") is None:
        return []

    items = data.get("items")
    if items is None:
        return []
    result: list[dict[Any, Any]] = items
    return result


def search_roles(
    api: privx_api.PrivXAPI,
    search_payload: dict[Any, Any],
    offset: int = 0,
    limit: int = 0,
) -> dict[Any, Any] | None:
    """
    Search roles from PrivX API with optional pagination parameters.

    Args:
        api: PrivX API client instance
        search_payload: Search payload dictionary
        offset: Starting offset for pagination (default: 0)
        limit: Maximum number of items to return (default: 0 = all)

    Returns:
        dict: Response data containing roles information with 'items' and 'count' keys.

    Example:
        # Get all roles
        data = search_roles(api, {})

        # Get paginated results
        data = search_roles(api, {}, offset=50, limit=50)
    """
    try:
        if limit == 0:
            response = api.search_roles(search_payload=search_payload)
        else:
            response = api.search_roles(
                offset=offset,
                limit=limit,
                search_payload=search_payload,
            )
    except privx_api.exceptions.InternalAPIException as e:
        handle_http_5xx_error(e, "search_roles")

    data = get_response_data(response, "search_roles")

    if data is None:
        return None
    result: dict[Any, Any] = data
    return result


def get_role_members(
    api: privx_api.PrivXAPI,
    role_id: str,
    limit: int | None = None,
    offset: int = 0,
) -> dict[Any, Any]:
    """
    Get role members from PrivX API.

    Args:
        api: PrivX API client instance
        role_id: Role ID
        limit: Maximum number of items to return (default: None = 50 for all)
        offset: Offset for pagination (default: 0)

    Returns:
        dict: Dict containing role members with 'items' and 'count' keys.
    """
    try:
        if limit is None:
            # Get all records with default pagination
            response = api.get_role_members(
                role_id=role_id,
                offset=offset,
                limit=50,
            )
        else:
            # Paginated request
            response = api.get_role_members(
                role_id=role_id,
                offset=offset,
                limit=limit,
            )
    except privx_api.exceptions.InternalAPIException as e:
        handle_http_5xx_error(e, f"get_role_members for role_id={role_id}")

    # Role may have been deleted but still referenced by host principal mappings.
    # Treat this as empty membership so access reports can continue gracefully.
    if not response.ok:
        error_code = response.data.get("details", {}).get("error_code", "UNKNOWN")
        status = response.status
        if status == 400 or status == 404 or error_code in ("BAD_REQUEST", "NOT_FOUND", "ROLE_NOT_FOUND"):
            logger.info(
                f"Role '{role_id}' not found (status={status}, error_code={error_code}), returning empty members list"
            )
            return {"count": 0, "items": []}

    data = get_response_data(response, "get_role_members")

    if not data or data.get("count") is None or data.get("items") is None:
        if response.data and isinstance(response.data, dict):
            status = response.data.get("status")
            error_code = response.data.get("details", {}).get("error_code", "UNKNOWN")
            if status == 400 or status == 404 or error_code in ("BAD_REQUEST", "NOT_FOUND", "ROLE_NOT_FOUND"):
                logger.info(
                    f"Role '{role_id}' not found (status={status}, error_code={error_code}), "
                    "returning empty members list"
                )
                return {"count": 0, "items": []}
        raise Exception(f"Failed to get role members: {data}")

    result: dict[Any, Any] = data
    return result


def get_user_roles(api: privx_api.PrivXAPI, user_id: str) -> list[dict[Any, Any]]:
    """
    Fetch all roles of a user from PrivX API.

    Returns:
        list[dict]: List of roles. Returns empty list if user doesn't exist.
    """
    try:
        response = api.get_user_roles(user_id)
    except privx_api.exceptions.InternalAPIException as e:
        handle_http_5xx_error(e, f"get_user_roles for user_id={user_id}")

    # Check if the response indicates the user doesn't exist (400 BAD_REQUEST or 404 USER_NOT_FOUND)
    if not response.ok:
        error_code = response.data.get("details", {}).get("error_code", "UNKNOWN")
        status = response.status
        if status == 400 or status == 404 or error_code in ("BAD_REQUEST", "USER_NOT_FOUND"):
            # User doesn't exist, return empty list gracefully
            logger.info(
                f"User '{user_id}' not found (status={status}, error_code={error_code}), returning empty roles list"
            )
            return []
        # For other errors, let get_response_data handle logging and return None
        # which will be caught below

    data = get_response_data(response, "get_user_roles")

    # Check if response contains an error status (other than user not found)
    if not data or data.get("count") is None or data.get("items") is None:
        # Check if this is a user-not-found error in the data structure
        if data and isinstance(data, dict):
            status = data.get("status")
            error_code = data.get("details", {}).get("error_code", "UNKNOWN")
            if status == 400 or status == 404 or error_code in ("BAD_REQUEST", "USER_NOT_FOUND"):
                logger.info(
                    f"User '{user_id}' not found (status={status}, error_code={error_code}), returning empty roles list"
                )
                return []
        raise Exception(f"Failed to get user roles: {data}")

    items = data.get("items")
    if items is None:
        raise Exception("Failed to get user roles: items is None")
    result: list[dict[Any, Any]] = items
    return result


def get_all_roles(api: privx_api.PrivXAPI) -> list[dict[Any, Any]]:
    """
    Get all roles with automatic pagination.

    Args:
        api: PrivX API client instance

    Returns:
        list: List of all role dictionaries
    """
    all_items: list[dict[Any, Any]] = []
    offset = 0
    limit = 1000

    while True:
        try:
            response = api.get_roles(offset=offset, limit=limit)
        except privx_api.exceptions.InternalAPIException as e:
            handle_http_5xx_error(e, f"get_roles for offset={offset}")

        data = get_response_data(response, "get_roles")
        if data is None:
            break

        items = data.get("items", [])
        count = data.get("count", 0)

        all_items.extend(items)

        logger.info(f"Fetched {len(items)} roles (offset={offset}, total so far={len(all_items)})")

        # If we got fewer items than the limit, we've reached the end
        if len(items) < limit:
            break

        # If we've fetched all items based on count
        if len(all_items) >= count:
            break

        offset += limit

    logger.info(f"Total roles fetched: {len(all_items)}")
    return all_items
