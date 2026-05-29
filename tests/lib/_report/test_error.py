"""Tests for error handling utilities."""

from unittest.mock import MagicMock, patch

import pytest

from lib._report.error import ConfigError, ReportError, ValidationError, handle_error

#### ReportError tests ####


@pytest.mark.unit
def test_report_error_with_message_only() -> None:
    """Test that ReportError correctly initializes with just a message."""
    error = ReportError("Something went wrong")

    assert error.message == "Something went wrong"
    assert error.usage is None
    assert error.prefix_usage is True
    assert str(error) == "Something went wrong"


@pytest.mark.unit
def test_report_error_with_message_and_usage() -> None:
    """Test that ReportError correctly initializes with message and usage information."""
    error = ReportError("Invalid input", usage="Use --help for more info")

    assert error.message == "Invalid input"
    assert error.usage == "Use --help for more info"
    assert error.prefix_usage is True


@pytest.mark.unit
def test_report_error_with_prefix_usage_false() -> None:
    """Test that ReportError correctly handles prefix_usage flag set to False."""
    error = ReportError("Error occurred", usage="Usage info", prefix_usage=False)

    assert error.message == "Error occurred"
    assert error.usage == "Usage info"
    assert error.prefix_usage is False


@pytest.mark.unit
def test_report_error_can_be_raised() -> None:
    """Test that ReportError can be raised and caught as an exception."""
    with pytest.raises(ReportError) as exc_info:
        raise ReportError("Test error")

    assert exc_info.value.message == "Test error"
    assert str(exc_info.value) == "Test error"


#### ConfigError tests ####


@pytest.mark.unit
def test_config_error_basic() -> None:
    """Test that ConfigError correctly initializes and inherits from ReportError."""
    error = ConfigError("Configuration is invalid")

    assert error.message == "Configuration is invalid"
    assert error.usage is None
    assert error.prefix_usage is True
    assert isinstance(error, ReportError)
    assert isinstance(error, Exception)


@pytest.mark.unit
def test_config_error_with_usage() -> None:
    """Test that ConfigError can include usage information."""
    error = ConfigError("Missing config file", usage="Check config.toml")

    assert error.message == "Missing config file"
    assert error.usage == "Check config.toml"


@pytest.mark.unit
def test_config_error_can_be_raised() -> None:
    """Test that ConfigError can be raised and caught as an exception."""
    with pytest.raises(ConfigError) as exc_info:
        raise ConfigError("Bad config")

    assert exc_info.value.message == "Bad config"


#### ValidationError tests ####


@pytest.mark.unit
def test_validation_error_basic() -> None:
    """Test that ValidationError correctly initializes and inherits from ReportError."""
    error = ValidationError("Validation failed")

    assert error.message == "Validation failed"
    assert error.usage is None
    assert error.prefix_usage is True
    assert isinstance(error, ReportError)
    assert isinstance(error, Exception)


@pytest.mark.unit
def test_validation_error_with_usage() -> None:
    """Test that ValidationError can include usage information."""
    error = ValidationError("Invalid field", usage="Field must be non-empty")

    assert error.message == "Invalid field"
    assert error.usage == "Field must be non-empty"


@pytest.mark.unit
def test_validation_error_can_be_raised() -> None:
    """Test that ValidationError can be raised and caught as an exception."""
    with pytest.raises(ValidationError) as exc_info:
        raise ValidationError("Invalid data")

    assert exc_info.value.message == "Invalid data"


#### handle_error tests ####


@pytest.mark.unit
@patch("lib._report.error.logger")
def test_handle_error_with_user_message_only(mock_logger: MagicMock) -> None:
    """Test that handle_error logs user message and returns it."""
    result = handle_error("User-facing error message")

    assert result == "User-facing error message"
    mock_logger.error.assert_called_once_with("User-facing error message")


@pytest.mark.unit
@patch("lib._report.error.logger")
def test_handle_error_with_user_and_log_messages(mock_logger: MagicMock) -> None:
    """Test that handle_error logs both user message and additional log message."""
    result = handle_error("User error", "Detailed log message")

    assert result == "User error"
    assert mock_logger.error.call_count == 2
    mock_logger.error.assert_any_call("User error")
    mock_logger.error.assert_any_call("Detailed log message")


@pytest.mark.unit
@patch("lib._report.error.logger")
def test_handle_error_with_none_log_message(mock_logger: MagicMock) -> None:
    """Test that handle_error correctly handles None as log_message parameter."""
    result = handle_error("Error occurred", None)

    assert result == "Error occurred"
    mock_logger.error.assert_called_once_with("Error occurred")


@pytest.mark.unit
@patch("lib._report.error.logger")
def test_handle_error_with_empty_log_message(mock_logger: MagicMock) -> None:
    """Test that handle_error doesn't log empty string log messages."""
    result = handle_error("Main error", "")

    assert result == "Main error"
    # Empty string is falsy, so should only call once
    mock_logger.error.assert_called_once_with("Main error")


@pytest.mark.unit
@patch("lib._report.error.logger")
def test_handle_error_returns_user_message_unchanged(_mock_logger: MagicMock) -> None:
    """Test that handle_error returns the exact user message without modification."""
    user_msg = "This is the exact error message"
    result = handle_error(user_msg, "Extra logging info")

    assert result == user_msg
    assert result is user_msg  # Same object reference
