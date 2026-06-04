"""Module for PrivX Network Targets API operations."""

import logging
from typing import Any

import privx_api
import privx_api.exceptions

from lib.clients.privx.http_error import handle_http_5xx_error
from lib.report_api._shared import get_response_data

logger = logging.getLogger(__name__)


def get_all_network_targets(api: privx_api.PrivXAPI) -> list[dict[Any, Any]]:
    """
    Get all network targets with automatic pagination.

    Args:
        api: PrivX API client instance

    Returns:
        list: List of all network target dictionaries
    """
    all_items: list[dict[Any, Any]] = []
    offset = 0
    limit = 1000

    while True:
        try:
            response = api.get_network_targets(offset=offset, limit=limit)
        except privx_api.exceptions.InternalAPIException as e:
            handle_http_5xx_error(e, f"get_network_targets for offset={offset}")

        data = get_response_data(response, "get_network_targets")
        if data is None:
            break

        items = data.get("items", [])
        count = data.get("count", 0)

        all_items.extend(items)

        logger.info(f"Fetched {len(items)} network targets (offset={offset}, total so far={len(all_items)})")

        # If we got fewer items than the limit, we've reached the end
        if len(items) < limit:
            break

        # If we've fetched all items based on count
        if len(all_items) >= count:
            break

        offset += limit

    logger.info(f"Total network targets fetched: {len(all_items)}")
    return all_items
