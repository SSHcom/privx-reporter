"""Tests for response utility functions."""

import pytest

from lib.utils.output.response import report_response


@pytest.mark.unit
def test_report_response_with_all_parameters() -> None:
    """Test that report_response creates correct dictionary with all parameters provided."""
    result = report_response(
        report_path="/path/to/report.csv",
        error_message="Something went wrong",
        info_message="Processing complete",
    )

    assert result["report_path"] == "/path/to/report.csv"
    assert result["error_message"] == "Something went wrong"
    assert result["info_message"] == "Processing complete"


@pytest.mark.unit
def test_report_response_with_no_parameters() -> None:
    """Test that report_response creates dictionary with default values when no parameters provided."""
    result = report_response()

    assert result["report_path"] == ""
    assert result["error_message"] is None
    assert result["info_message"] is None


@pytest.mark.unit
def test_report_response_with_report_path_only() -> None:
    """Test that report_response correctly handles only report_path parameter."""
    result = report_response(report_path="/output/report.json")

    assert result["report_path"] == "/output/report.json"
    assert result["error_message"] is None
    assert result["info_message"] is None


@pytest.mark.unit
def test_report_response_with_error_message_only() -> None:
    """Test that report_response correctly handles only error_message parameter."""
    result = report_response(error_message="Error occurred")

    assert result["report_path"] == ""
    assert result["error_message"] == "Error occurred"
    assert result["info_message"] is None


@pytest.mark.unit
def test_report_response_with_info_message_only() -> None:
    """Test that report_response correctly handles only info_message parameter."""
    result = report_response(info_message="Info message")

    assert result["report_path"] == ""
    assert result["error_message"] is None
    assert result["info_message"] == "Info message"


@pytest.mark.unit
def test_report_response_with_empty_strings() -> None:
    """Test that report_response correctly handles empty string values."""
    result = report_response(report_path="", error_message="", info_message="")

    assert result["report_path"] == ""
    assert result["error_message"] == ""
    assert result["info_message"] == ""


@pytest.mark.unit
def test_report_response_return_type_is_dict() -> None:
    """Test that report_response returns a dictionary."""
    result = report_response()

    assert isinstance(result, dict)
    assert "report_path" in result
    assert "error_message" in result
    assert "info_message" in result


@pytest.mark.unit
def test_report_response_with_error_and_info() -> None:
    """Test that report_response can have both error and info messages."""
    result = report_response(
        error_message="Warning: partial failure",
        info_message="10 items processed",
    )

    assert result["report_path"] == ""
    assert result["error_message"] == "Warning: partial failure"
    assert result["info_message"] == "10 items processed"
