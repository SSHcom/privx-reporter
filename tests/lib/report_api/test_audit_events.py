"""Tests for audit events API functions."""

from unittest.mock import MagicMock

import privx_api.exceptions
import pytest

from lib.report_api.audit_events import get_audit_events


@pytest.mark.unit
def test_get_audit_events_success(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_audit_events correctly retrieves audit events using default pagination and sorting parameters."""
    mock_response.data = {
        "count": 2,
        "items": [
            {"id": "event1", "created": "2024-01-01T00:00:00Z", "action": "login"},
            {"id": "event2", "created": "2024-01-01T01:00:00Z", "action": "logout"},
        ],
    }
    mock_api.search_audit_events.return_value = mock_response

    result = get_audit_events(mock_api)

    assert result["count"] == 2
    assert len(result["items"]) == 2
    mock_api.search_audit_events.assert_called_once()
    call_kwargs = mock_api.search_audit_events.call_args.kwargs
    assert call_kwargs["offset"] == 0
    assert call_kwargs["limit"] == 100
    assert call_kwargs["sort_dir"] == "asc"
    assert call_kwargs["audit_event_params"]["sort_key"] == "created"


@pytest.mark.unit
def test_get_audit_events_with_custom_parameters(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_audit_events correctly applies custom parameters for time range, sorting, pagination, and limit."""
    mock_response.data = {
        "count": 1,
        "items": [{"id": "event1", "created": "2024-01-01T00:00:00Z"}],
    }
    mock_api.search_audit_events.return_value = mock_response

    result = get_audit_events(
        mock_api,
        start_time="2024-01-01T00:00:00Z",
        end_time="2024-01-01T23:59:59Z",
        sort_dir="desc",
        sort_key="action",
        limit=50,
        offset=10,
    )

    assert result["count"] == 1
    call_kwargs = mock_api.search_audit_events.call_args.kwargs
    assert call_kwargs["offset"] == 10
    assert call_kwargs["limit"] == 50
    assert call_kwargs["sort_dir"] == "desc"
    assert call_kwargs["audit_event_params"]["start_time"] == "2024-01-01T00:00:00Z"
    assert call_kwargs["audit_event_params"]["end_time"] == "2024-01-01T23:59:59Z"
    assert call_kwargs["audit_event_params"]["sort_key"] == "action"


@pytest.mark.unit
def test_get_audit_events_with_invalid_response_raises_exception(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_audit_events raises an exception when response data is invalid."""
    mock_response.data = {"count": None, "items": [{"id": "event1"}]}
    mock_api.search_audit_events.return_value = mock_response

    with pytest.raises(Exception, match="Failed to get audit events"):
        get_audit_events(mock_api)


@pytest.mark.unit
def test_get_audit_events_propagates_errors_when_requested(mock_api: MagicMock) -> None:
    api_exception = privx_api.exceptions.InternalAPIException("Invalid response", 503)
    mock_api.search_audit_events.side_effect = api_exception

    with pytest.raises(privx_api.exceptions.InternalAPIException):
        get_audit_events(mock_api, propagate_errors=True)
