import logging
from typing import Any

import privx_api
import privx_api.exceptions

from lib.clients.privx.http_error import handle_http_5xx_error
from lib.report_api._shared import get_response_data, get_response_data_object

logger = logging.getLogger(__name__)


def get_connection(
    api: privx_api.PrivXAPI,
    connection_id: str,
) -> dict[Any, Any] | None:
    """
    Get a single connection from PrivX API.

    Args:
        api: PrivX API client instance
        connection_id: Connection ID

    Returns:
        dict | None: Response data containing connection information, or None if connection doesn't exist.
    """

    try:
        response = api.get_connection(connection_id=connection_id)
    except privx_api.exceptions.InternalAPIException as e:
        handle_http_5xx_error(e, "get_connection")

    # Check if the response indicates the connection doesn't exist (400 BAD_REQUEST or 404 NOT_FOUND)
    if not response.ok:
        error_code = response.data.get("details", {}).get("error_code", "UNKNOWN")
        status = response.status
        if status == 400 or status == 404 or error_code in ("BAD_REQUEST", "NOT_FOUND", "CONNECTION_NOT_FOUND"):
            # Connection doesn't exist, return None gracefully
            logger.info(
                f"Connection '{connection_id}' not found (status={status}, error_code={error_code}), returning None"
            )
            return None
        # For other errors, let get_response_data_object handle logging and return None
        # which will be caught below

    data = get_response_data_object(response, "get_connection")

    # Check if response contains an error status (other than connection not found)
    if not data:
        # Check if this is a connection-not-found error in the response
        if response.data and isinstance(response.data, dict):
            status = response.data.get("status")
            error_code = response.data.get("details", {}).get("error_code", "UNKNOWN")
            if status == 400 or status == 404 or error_code in ("BAD_REQUEST", "NOT_FOUND", "CONNECTION_NOT_FOUND"):
                logger.info(
                    f"Connection '{connection_id}' not found (status={status}, error_code={error_code}), returning None"
                )
                return None
        raise Exception(f"Failed to get connection: {data}")

    result: dict[Any, Any] = data
    return result


def search_connections(
    api: privx_api.PrivXAPI,
    offset: int = 0,
    limit: int | None = None,
    sort_key: str | None = None,
    sort_dir: str | None = None,
    search_payload: dict | None = None,
    propagate_errors: bool = False,
) -> dict[Any, Any]:
    """
    Search connections from PrivX API.

    Args:
        api: PrivX API client instance
        offset: Number of results to skip (default: 0)
        limit: Maximum number of results to return (default: None = 50 for all)
        sort_key: Optional sort key
        sort_dir: Optional sort direction
        search_payload: Search payload dictionary

    Returns:
        dict: Response data containing connections information with 'items' and 'count' keys.
    """

    try:
        if limit is None:
            # Get all records with default pagination
            response = api.search_connections(
                offset=offset, limit=50, sort_key=sort_key, sort_dir=sort_dir, connection_params=search_payload
            )
        else:
            # Paginated request
            response = api.search_connections(
                offset=offset, limit=limit, sort_key=sort_key, sort_dir=sort_dir, connection_params=search_payload
            )
    except privx_api.exceptions.InternalAPIException as e:
        if propagate_errors:
            raise
        handle_http_5xx_error(e, "search_connections")

    data = get_response_data(response, "search_connections")

    if not data or data.get("count") is None or data.get("items") is None:
        raise Exception(f"Failed to search connections: {data}")

    result: dict[Any, Any] = data
    return result
