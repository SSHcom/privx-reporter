"""Module for PrivX Access Groups API operations."""

import logging
from typing import Any

import privx_api
import privx_api.exceptions

from lib.clients.privx.http_error import handle_http_5xx_error
from lib.report_api._shared import get_response_data, get_response_data_object

logger = logging.getLogger(__name__)


def get_access_group_by_id(api: privx_api.PrivXAPI, id: str) -> dict[Any, Any] | None:
    """
    Get an access group by id.

    Returns:
        dict | None: Access group dictionary with all fields, or None if not found
    """

    try:
        response = api.get_access_group(id)

    except privx_api.exceptions.InternalAPIException as e:
        handle_http_5xx_error(e, f"get_access_group_by_id for id={id}")

    data = get_response_data_object(response, "get_access_group_by_id")
    if data is None:
        return None
    result: dict[Any, Any] = data
    return result


def search_access_groups(
    api: privx_api.PrivXAPI,
    offset: int = 0,
    limit: int = 0,
    search_payload: dict[Any, Any] | None = None,
) -> dict[Any, Any] | None:
    """
    Search access groups from PrivX API.

    Args:
        api: PrivX API client instance
        offset: Offset for pagination (default: 0)
        limit: Maximum number of items to return (default: 0 = all)
        search_payload: Optional search payload dictionary

    Returns:
        dict | None: Response data containing access groups with 'items' and 'count' keys, or None if error
    """
    try:
        if limit == 0:
            # Get all records - don't pass offset/limit
            response = api.search_access_groups(
                access_group_params=search_payload,
            )
        else:
            # Paginated request
            response = api.search_access_groups(
                offset=offset,
                limit=limit,
                access_group_params=search_payload,
            )
    except privx_api.exceptions.InternalAPIException as e:
        handle_http_5xx_error(e, "search_access_groups")

    data = get_response_data(response, "search_access_groups")

    if data is None:
        return None
    result: dict[Any, Any] = data
    return result
