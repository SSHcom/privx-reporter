"""Tests for retry helpers."""

from unittest.mock import MagicMock, patch

import privx_api.exceptions
import pytest

from lib.clients.privx.retry import RetryExhausted, with_retry


@pytest.mark.unit
def test_with_retry_retries_then_succeeds() -> None:
    fn = MagicMock(side_effect=[privx_api.exceptions.InternalAPIException("tmp", 503), "ok"])

    with patch("lib.clients.privx.retry.time.sleep") as mock_sleep:
        result = with_retry(fn, max_attempts=3, base_delay=0.01, operation="test-call")

    assert result == "ok"
    assert fn.call_count == 2
    mock_sleep.assert_called_once()


@pytest.mark.unit
def test_with_retry_raises_retry_exhausted() -> None:
    fn = MagicMock(side_effect=privx_api.exceptions.InternalAPIException("tmp", 504))

    with patch("lib.clients.privx.retry.time.sleep"):
        with pytest.raises(RetryExhausted):
            with_retry(fn, max_attempts=2, base_delay=0.01, operation="test-call")


@pytest.mark.unit
def test_with_retry_does_not_retry_non_retryable() -> None:
    fn = MagicMock(side_effect=ValueError("bad input"))

    with pytest.raises(ValueError, match="bad input"):
        with_retry(fn, max_attempts=3, base_delay=0.01)

    assert fn.call_count == 1
