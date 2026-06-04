import logging
from typing import Any

import privx_api
import privx_api.exceptions

from lib.clients.privx.http_error import handle_http_5xx_error
from lib.report_api._shared import get_response_data, get_response_data_object

logger = logging.getLogger(__name__)


def get_host(
    api: privx_api.PrivXAPI,
    host_id: str,
) -> dict[Any, Any]:
    """
    Get a single host from PrivX API.

    Args:
        api: PrivX API client instance
        host_id: Host ID

    Returns:
        dict: Response data containing host information.
    """

    try:
        response = api.get_host(host_id=host_id)
    except privx_api.exceptions.InternalAPIException as e:
        handle_http_5xx_error(e, "get_host")

    data = get_response_data_object(response, "get_host")

    if not data:
        raise Exception(f"Failed to get host: {data}")

    result: dict[Any, Any] = data
    return result


def search_hosts(
    api: privx_api.PrivXAPI,
    search_payload: dict[Any, Any],
    offset: int = 0,
    limit: int = 0,
) -> dict[Any, Any] | None:
    """
    Search hosts from PrivX API with optional pagination parameters.

    Args:
        api: PrivX API client instance
        search_payload: Search payload dictionary
        offset: Starting offset for pagination (default: 0)
        limit: Maximum number of items to return (default: 0 = all)

    Returns:
        dict: Response data containing hosts information with 'items' and 'count' keys.

    Example:
        # Get all hosts
        data = search_hosts(api, {"keywords": "web"})

        # Get paginated results
        data = search_hosts(api, {"keywords": "web"}, offset=50, limit=50)
    """
    try:
        if limit == 0:
            # Get all records - don't pass offset/limit
            response = api.search_hosts(search_payload=search_payload)
        else:
            # Paginated request
            response = api.search_hosts(
                offset=offset,
                limit=limit,
                search_payload=search_payload,
            )
    except privx_api.exceptions.InternalAPIException as e:
        handle_http_5xx_error(e, "search_hosts")

    data = get_response_data(response, "search_hosts")

    if data is None:
        return None

    if data.get("count") is None or data.get("items") is None:
        raise Exception(f"Failed to search hosts: {data}")

    result: dict[Any, Any] = data
    return result


def get_all_hosts(api: privx_api.PrivXAPI) -> list[dict[Any, Any]]:
    """
    Get all hosts with automatic pagination.

    Args:
        api: PrivX API client instance

    Returns:
        list: List of all host dictionaries
    """
    all_items: list[dict[Any, Any]] = []
    offset = 0
    limit = 1000

    while True:
        try:
            response = api.get_hosts(offset=offset, limit=limit)
        except privx_api.exceptions.InternalAPIException as e:
            handle_http_5xx_error(e, f"get_hosts for offset={offset}")

        data = get_response_data(response, "get_hosts")
        if data is None:
            break

        items = data.get("items", [])
        count = data.get("count", 0)

        all_items.extend(items)

        logger.info(f"Fetched {len(items)} hosts (offset={offset}, total so far={len(all_items)})")

        # If we got fewer items than the limit, we've reached the end
        if len(items) < limit:
            break

        # If we've fetched all items based on count
        if len(all_items) >= count:
            break

        offset += limit

    logger.info(f"Total hosts fetched: {len(all_items)}")
    return all_items
