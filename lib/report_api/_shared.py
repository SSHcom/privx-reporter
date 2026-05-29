# Tests are not necessary for this module.

import logging
from typing import Any

from privx_api import PrivXAPIResponse

logger = logging.getLogger(__name__)


def get_response_data(resp: PrivXAPIResponse, operation: str) -> dict[Any, Any] | None:
    if not resp.ok:
        error_code = resp.data.get("details", {}).get("error_code", "UNKNOWN")
        logger.error(f"Error {operation}: status={resp.status}, error_code={error_code}")
        return None

    data_load = resp.data

    if "status" in data_load and data_load.get("status") >= 400:
        status = data_load.get("status")
        error_code = data_load.get("details", {}).get("error_code", "UNKNOWN")
        logger.error(f"Error {operation}: status={status}, error_code={error_code}")
        return None

    data: dict[Any, Any] = data_load
    return data


def get_response_data_object(resp: PrivXAPIResponse, operation: str) -> dict[Any, Any] | None:
    """Get response data for direct object responses (not wrapped in status structures).

    This is used for API calls that return a single object directly, such as get_connection,
    rather than responses wrapped in structures with 'items' and 'count' fields.

    Args:
        resp: PrivX API response object
        operation: Operation name for logging purposes

    Returns:
        dict: Response data object, or None if there was an error
    """
    if not resp.ok:
        error_code = resp.data.get("details", {}).get("error_code", "UNKNOWN")
        logger.error(f"Error {operation}: status={resp.status}, error_code={error_code}")
        return None

    # For direct object responses, just return the data directly
    data: dict[Any, Any] = resp.data
    return data
