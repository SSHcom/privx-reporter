import logging
from typing import Any

import privx_api
import privx_api.exceptions

from lib.clients.privx.http_error import handle_http_5xx_error
from lib.report_api._shared import get_response_data

logger = logging.getLogger(__name__)


def get_audit_events(
    api: privx_api.PrivXAPI,
    start_time: str | None = None,
    end_time: str | None = None,
    sort_dir: str = "asc",
    sort_key: str = "created",
    limit: int | None = None,
    offset: int = 0,
    propagate_errors: bool = False,
) -> dict[Any, Any]:
    """
    Get audit events from PrivX API.

    Args:
        api: PrivX API client instance
        start_time: Optional start time filter
        end_time: Optional end time filter
        sort_dir: Sort direction (default: "asc")
        sort_key: Sort key (default: "created")
        limit: Maximum number of items to return (default: None = 100 for all)
        offset: Offset for pagination (default: 0)

    Returns:
        dict: Dict audit events.
    """
    params = {
        "start_time": start_time,
        "end_time": end_time,
        "sort_key": sort_key,
    }

    try:
        if limit is None:
            # Get all records with default pagination
            response = api.search_audit_events(offset=offset, limit=100, sort_dir=sort_dir, audit_event_params=params)
        else:
            # Paginated request
            response = api.search_audit_events(offset=offset, limit=limit, sort_dir=sort_dir, audit_event_params=params)
    except privx_api.exceptions.InternalAPIException as e:
        if propagate_errors:
            raise
        handle_http_5xx_error(e, "get_audit_events")

    data = get_response_data(response, "get_audit_events")

    if not data or data.get("count") is None or data.get("items") is None:
        raise Exception(f"Failed to get audit events: {response.data}")

    result: dict[Any, Any] = data
    return result
