"""Shared utilities for PrivX API operations."""

import logging
import re
import socket
import sys

import privx_api.exceptions

logger = logging.getLogger(__name__)

_CONNECTION_ERROR_TYPES = (
    socket.gaierror,
    ConnectionRefusedError,
    TimeoutError,
    OSError,
)


def _exit_on_http_error(status_code: int, operation: str) -> None:
    """
    Exit gracefully on HTTP error status codes.

    Args:
        status_code: HTTP status code
        operation: Description of the operation that failed
    """
    if status_code < 400:
        return
    logger.error(f"HTTP {status_code} error during {operation}")
    if status_code == 401:
        logger.error("PrivX API authentication failed (401 Unauthorized).")
        logger.error(
            "Please check PRIVX_API_CLIENT_ID, PRIVX_API_CLIENT_SECRET, "
            "PRIVX_API_OAUTH_CLIENT_ID, and PRIVX_API_OAUTH_CLIENT_SECRET."
        )
    elif status_code == 403:
        logger.error("PrivX API access denied (403 Forbidden).")
        logger.error("The API client may lack the required permissions.")
    elif status_code == 503:
        logger.error("PrivX API server is unavailable (503 Service Unavailable).")
        logger.error("Please ensure the PrivX server is running and accessible.")
    elif 500 <= status_code < 600:
        logger.error("PrivX API server error. Please try again later.")
    else:
        logger.error("Please check your PrivX configuration.")
    sys.exit(1)


def is_connection_error(e: Exception) -> bool:
    """Return True if the exception (or its cause) is a network connection error."""
    if isinstance(e, _CONNECTION_ERROR_TYPES):
        return True
    cause = getattr(e, "__cause__", None) or getattr(e, "__context__", None)
    if cause is not None and isinstance(cause, _CONNECTION_ERROR_TYPES):
        return True
    # InternalAPIException wraps the original error in args[0]
    if e.args and isinstance(e.args[0], _CONNECTION_ERROR_TYPES):
        return True
    return False


def handle_http_5xx_error(e: Exception, operation: str) -> None:
    """
    Handle PrivX API errors by logging and exiting gracefully.

    Covers connection errors, HTTP 4xx/5xx responses, SSL errors, and other
    InternalAPIException variants so callers never receive an unhandled exception.

    Args:
        e: The exception that was raised
        operation: Description of the operation that failed
    """
    if is_connection_error(e):
        cause = (
            getattr(e, "__cause__", None)
            or getattr(e, "__context__", None)
            or (e.args[0] if e.args and isinstance(e.args[0], Exception) else None)
        )
        detail = str(cause) if cause else str(e)
        logger.error(f"Cannot connect to PrivX server during {operation}: {detail}")
        logger.error("Please check PRIVX_HOSTNAME and that the server is reachable.")
        sys.exit(1)

    status_code = None
    if isinstance(e, privx_api.exceptions.InternalAPIException):
        # Extract status code from exception args (e.g., ('Invalid response: ', 401))
        if len(e.args) > 1 and isinstance(e.args[1], int):
            status_code = e.args[1]
        elif hasattr(e, "status"):
            status_code = e.status
        elif hasattr(e, "response") and hasattr(e.response, "status"):
            status_code = e.response.status
        # Try to extract from exception message string
        elif len(e.args) > 0:
            match = re.search(r"\b([4-5]\d{2})\b", str(e))
            if match:
                status_code = int(match.group(1))

    if status_code is not None and status_code >= 400:
        _exit_on_http_error(status_code, operation)
        return

    # Unrecognised InternalAPIException — log and exit rather than propagating
    # into callers where the response variable may be unbound.
    if isinstance(e, privx_api.exceptions.InternalAPIException):
        logger.error(f"PrivX API error during {operation}: {e}")
        sys.exit(1)

    raise e
