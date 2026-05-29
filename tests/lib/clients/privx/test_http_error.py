"""Tests for HTTP error handling utilities."""

from unittest.mock import MagicMock, patch

import privx_api.exceptions
import pytest

from lib.clients.privx import http_error as http_error_module


@pytest.mark.unit
def test_handle_http_5xx_error_with_status_in_args() -> None:
    """Test handling error with status code in exception args tuple."""
    exception = privx_api.exceptions.InternalAPIException("Invalid response: ", 503)

    with patch.object(http_error_module, "_exit_on_http_error") as mock_exit:
        http_error_module.handle_http_5xx_error(exception, "test_operation")
        mock_exit.assert_called_once_with(503, "test_operation")


@pytest.mark.unit
def test_handle_http_5xx_error_with_status_attribute() -> None:
    """Test handling error with status attribute on exception."""
    exception = privx_api.exceptions.InternalAPIException("Error occurred")
    exception.status = 500  # type: ignore[attr-defined]

    with patch.object(http_error_module, "_exit_on_http_error") as mock_exit:
        http_error_module.handle_http_5xx_error(exception, "test_operation")
        mock_exit.assert_called_once_with(500, "test_operation")


@pytest.mark.unit
def test_handle_http_5xx_error_with_response_status() -> None:
    """Test handling error with status in response object."""
    exception = privx_api.exceptions.InternalAPIException("Error occurred")
    exception.response = MagicMock()  # type: ignore[attr-defined]
    exception.response.status = 502  # type: ignore[attr-defined]

    with patch.object(http_error_module, "_exit_on_http_error") as mock_exit:
        http_error_module.handle_http_5xx_error(exception, "test_operation")
        mock_exit.assert_called_once_with(502, "test_operation")


@pytest.mark.unit
def test_handle_http_5xx_error_with_status_in_message() -> None:
    """Test handling error by extracting status code from message string."""
    exception = privx_api.exceptions.InternalAPIException("Server error 504 occurred")

    with patch.object(http_error_module, "_exit_on_http_error") as mock_exit:
        http_error_module.handle_http_5xx_error(exception, "test_operation")
        mock_exit.assert_called_once_with(504, "test_operation")


@pytest.mark.unit
def test_handle_http_5xx_error_prioritizes_args_over_message() -> None:
    """Test that status in args is prioritized over message parsing."""
    exception = privx_api.exceptions.InternalAPIException("Error 504", 503)

    with patch.object(http_error_module, "_exit_on_http_error") as mock_exit:
        http_error_module.handle_http_5xx_error(exception, "test_operation")
        mock_exit.assert_called_once_with(503, "test_operation")


@pytest.mark.unit
def test_handle_http_5xx_error_4xx_in_message_calls_exit() -> None:
    """Test that 4xx status codes in message are handled."""
    exception = privx_api.exceptions.InternalAPIException("Error 404 not found")

    with patch.object(http_error_module, "_exit_on_http_error") as mock_exit:
        http_error_module.handle_http_5xx_error(exception, "test_operation")
        mock_exit.assert_called_once_with(404, "test_operation")


@pytest.mark.unit
def test_handle_http_5xx_error_no_status_code_exits() -> None:
    """Test that InternalAPIException without status code causes exit."""
    exception = privx_api.exceptions.InternalAPIException("Generic error")

    with pytest.raises(SystemExit):
        http_error_module.handle_http_5xx_error(exception, "test_operation")


@pytest.mark.unit
def test_handle_http_5xx_error_non_internal_api_exception_exits() -> None:
    """Test that non-InternalAPIException types cause exit (in test env all are InternalAPIException)."""
    exception = ValueError("Some other error")

    with pytest.raises(SystemExit):
        http_error_module.handle_http_5xx_error(exception, "test_operation")


@pytest.mark.unit
def test_handle_http_5xx_error_empty_args_exits() -> None:
    """Test handling error with empty args causes exit."""
    exception = privx_api.exceptions.InternalAPIException()

    with pytest.raises(SystemExit):
        http_error_module.handle_http_5xx_error(exception, "test_operation")


@pytest.mark.unit
def test_handle_http_5xx_error_status_511() -> None:
    """Test handling 511 Network Authentication Required error."""
    exception = privx_api.exceptions.InternalAPIException("Error", 511)

    with patch.object(http_error_module, "_exit_on_http_error") as mock_exit:
        http_error_module.handle_http_5xx_error(exception, "test_operation")
        mock_exit.assert_called_once_with(511, "test_operation")


@pytest.mark.unit
def test_is_connection_error_detects_connection_refused() -> None:
    assert http_error_module.is_connection_error(ConnectionRefusedError("refused")) is True
