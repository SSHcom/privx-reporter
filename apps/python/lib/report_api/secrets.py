"""Module for PrivX Roles API operations."""

import logging
from typing import Any

import privx_api
import privx_api.exceptions

from lib.clients.privx.http_error import handle_http_5xx_error
from lib.report_api._shared import get_response_data

logger = logging.getLogger(__name__)


def get_secrets(api: privx_api.PrivXAPI) -> dict[Any, Any] | None:
    """
    Get host secrets.

    Returns:
        dict | None: List of host secrets dictionary with all fields, or None if not found
    """
    try:
        response = api.get_secrets()
    except privx_api.exceptions.InternalAPIException as e:
        handle_http_5xx_error(e, "get_secrets")

    data = get_response_data(response, "get_secrets")
    if data is None:
        return None
    result: dict[Any, Any] = data
    return result


def search_secrets(
    api: privx_api.PrivXAPI,
    offset: int = 0,
    limit: int | None = None,
    sort_key: str | None = None,
    sort_dir: str | None = None,
    search_payload: dict | None = None,
) -> dict[Any, Any]:
    """
    Search secrets from PrivX API.

    Unlike get_secrets which only returns secrets the client has access to,
    search_secrets returns basic info for all secrets regardless of access.

    Args:
        api: PrivX API client instance
        offset: Number of results to skip (default: 0)
        limit: Maximum number of results to return (default: None = 50 for all)
        sort_key: Optional sort key
        sort_dir: Optional sort direction
        search_payload: Search payload dictionary

    Returns:
        dict: Response data containing secrets with 'items' and 'count' keys.
    """
    effective_limit = 50 if limit is None else limit

    try:
        response = api.search_secrets(
            offset=offset,
            limit=effective_limit,
            sort_key=sort_key,
            sort_dir=sort_dir,
            search_payload=search_payload,
        )
    except privx_api.exceptions.InternalAPIException as e:
        handle_http_5xx_error(e, "search_secrets")

    data = get_response_data(response, "search_secrets")

    if not data or data.get("count") is None or data.get("items") is None:
        raise Exception(f"Failed to search secrets: {data}")

    result: dict[Any, Any] = data
    return result
