"""Retry helpers for transient PrivX API failures."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import privx_api.exceptions

from lib.clients.privx.http_error import is_connection_error

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable

RETRYABLE_STATUS_CODES = {429, 502, 503, 504}


class RetryExhaustedError(Exception):
    """Raised when all retry attempts for an operation are exhausted."""

    def __init__(self, last_error: Exception, attempts: int) -> None:
        self.last_error = last_error
        self.attempts = attempts
        super().__init__(f"Retry exhausted after {attempts} attempts: {last_error}")


RetryExhausted = RetryExhaustedError


def _extract_status_code(error: Exception) -> int | None:
    if not isinstance(error, privx_api.exceptions.InternalAPIException):
        return None
    if len(error.args) > 1 and isinstance(error.args[1], int):
        return error.args[1]
    return None


def is_retryable(error: Exception) -> bool:
    if is_connection_error(error):
        return True
    status_code = _extract_status_code(error)
    return status_code is not None and status_code in RETRYABLE_STATUS_CODES


def with_retry[T](
    fn: Callable[[], T],
    max_attempts: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    operation: str = "API call",
) -> T:
    """Execute ``fn`` with exponential backoff for retryable failures."""
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as error:
            if not is_retryable(error):
                raise

            last_error = error
            status_code = _extract_status_code(error)

            if attempt == max_attempts:
                logger.error(
                    "%s failed after %s attempts (HTTP %s)",
                    operation,
                    max_attempts,
                    status_code,
                )
                raise RetryExhaustedError(error, max_attempts) from error

            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            logger.warning(
                "%s failed (HTTP %s), attempt %s/%s; retrying in %.1fs",
                operation,
                status_code,
                attempt,
                max_attempts,
                delay,
            )
            time.sleep(delay)

    # Defensive fallback, loop always returns or raises.
    raise RetryExhaustedError(last_error or RuntimeError("unknown retry error"), max_attempts)
