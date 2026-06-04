"""Tests for connections API functions."""

from unittest.mock import MagicMock

import privx_api.exceptions
import pytest

from lib.report_api.connections import get_connection, search_connections


@pytest.mark.unit
def test_get_connection_success(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_connection retrieves a single connection by ID."""
    mock_response.data = {
        "id": "conn-123",
        "created": "2026-01-02T10:00:00Z",
        "connected": "2026-01-02T10:00:30Z",
        "disconnected": "2026-01-02T10:15:00Z",
        "duration": 870,
        "status": "TERMINATED",
        "type": "SSH",
        "user": {
            "id": "user-1",
            "display_name": "John Doe",
        },
        "target_host": {
            "id": "host-1",
            "common_name": "server1.example.com",
        },
        "target_host_address": "192.168.1.10",
        "target_host_account": "root",
    }
    mock_api.get_connection.return_value = mock_response

    result = get_connection(mock_api, "conn-123")

    assert result["id"] == "conn-123"
    assert result["user"]["id"] == "user-1"
    assert result["target_host"]["common_name"] == "server1.example.com"
    mock_api.get_connection.assert_called_once_with(connection_id="conn-123")


@pytest.mark.unit
@pytest.mark.parametrize(
    "status_code,error_code,connection_id",
    [
        (404, "NOT_FOUND", "conn-nonexistent"),
        (400, "BAD_REQUEST", "no-connection"),
    ],
)
def test_get_connection_with_connection_not_found(
    mock_api: MagicMock,
    mock_response: MagicMock,
    status_code: int,
    error_code: str,
    connection_id: str,
) -> None:
    """Test that get_connection returns None when connection is not found (404 or 400 error)."""
    mock_response.ok = False
    mock_response.status = status_code
    mock_response.data = {"details": {"error_code": error_code}}
    mock_api.get_connection.return_value = mock_response

    result = get_connection(mock_api, connection_id)
    assert result is None


@pytest.mark.unit
@pytest.mark.parametrize(
    "status_code,error_code,connection_id",
    [
        (500, "INTERNAL_ERROR", "conn-123"),
        (403, "FORBIDDEN", "conn-123"),
    ],
)
def test_get_connection_with_response_not_ok(
    mock_api: MagicMock,
    mock_response: MagicMock,
    status_code: int,
    error_code: str,
    connection_id: str,
) -> None:
    """Test that get_connection raises an exception when API response indicates an error (other than not found)."""
    mock_response.ok = False
    mock_response.status = status_code
    mock_response.data = {"details": {"error_code": error_code}}
    mock_api.get_connection.return_value = mock_response

    with pytest.raises(Exception, match="Failed to get connection"):
        get_connection(mock_api, connection_id)


@pytest.mark.unit
def test_get_connection_with_empty_response_data(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_connection raises an exception when response data is empty."""
    mock_response.data = None
    mock_api.get_connection.return_value = mock_response

    with pytest.raises(Exception, match="Failed to get connection"):
        get_connection(mock_api, "conn-123")


@pytest.mark.unit
def test_get_connection_handles_internal_api_exception(
    mock_api: MagicMock, mock_handle_http_5xx_error: MagicMock
) -> None:
    """Test that get_connection delegates InternalAPIException handling."""
    api_exception = privx_api.exceptions.InternalAPIException("500 Internal Server Error")
    mock_api.get_connection.side_effect = api_exception

    # Mock handle_http_5xx_error to re-raise so we can verify it was called
    mock_handle_http_5xx_error.side_effect = api_exception

    with pytest.raises(privx_api.exceptions.InternalAPIException):
        get_connection(mock_api, "conn-123")

    mock_handle_http_5xx_error.assert_called_once_with(api_exception, "get_connection")


@pytest.mark.unit
def test_search_connections_success(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that search_connections retrieves connection search results."""
    mock_response.data = {
        "count": 2,
        "items": [
            {
                "id": "conn-1",
                "user": {"id": "user-1", "display_name": "John Doe"},
                "target_host": {"id": "host-1", "common_name": "server1"},
            },
            {
                "id": "conn-2",
                "user": {"id": "user-2", "display_name": "Jane Smith"},
                "target_host": {"id": "host-2", "common_name": "server2"},
            },
        ],
    }
    mock_api.search_connections.return_value = mock_response

    search_payload = {
        "connected": {"start_time": "2026-01-01T00:00:00Z"},
        "disconnected": {"end": "2026-01-10T23:59:59Z"},
    }
    result = search_connections(mock_api, offset=10, limit=25, search_payload=search_payload)

    assert result["count"] == 2
    assert len(result["items"]) == 2
    assert result["items"][0]["id"] == "conn-1"
    assert result["items"][1]["id"] == "conn-2"
    mock_api.search_connections.assert_called_once_with(
        offset=10, limit=25, sort_key=None, sort_dir=None, connection_params=search_payload
    )


@pytest.mark.unit
def test_search_connections_with_sort_parameters(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that search_connections correctly applies sort parameters (sort_key and sort_dir) when provided."""
    mock_response.data = {"count": 1, "items": [{"id": "conn-1"}]}
    mock_api.search_connections.return_value = mock_response

    result = search_connections(mock_api, sort_key="connected", sort_dir="DESC")

    assert result["count"] == 1
    mock_api.search_connections.assert_called_once_with(
        offset=0,
        limit=50,
        sort_key="connected",
        sort_dir="DESC",
        connection_params=None,
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "response_ok,status_code,data",
    [
        (False, 500, {"details": {"error_code": "INTERNAL_ERROR"}}),
        (True, 200, {"status": 400, "details": {"error_code": "BAD_REQUEST"}}),
    ],
)
def test_search_connections_with_error_response(
    mock_api: MagicMock,
    mock_response: MagicMock,
    response_ok: bool,
    status_code: int,
    data: dict,
) -> None:
    """Test that search_connections raises an exception for various error scenarios."""
    mock_response.ok = response_ok
    mock_response.status = status_code
    mock_response.data = data
    mock_api.search_connections.return_value = mock_response

    with pytest.raises(Exception, match="Failed to search connections"):
        search_connections(mock_api, search_payload={"user": {"id": "user-1"}})


@pytest.mark.unit
def test_search_connections_with_invalid_response_data(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that search_connections raises an exception when response data is invalid."""
    mock_response.data = {"count": None, "items": []}
    mock_api.search_connections.return_value = mock_response

    with pytest.raises(Exception, match="Failed to search connections"):
        search_connections(mock_api)


@pytest.mark.unit
def test_search_connections_handles_internal_api_exception(
    mock_api: MagicMock, mock_handle_http_5xx_error: MagicMock
) -> None:
    """Test that search_connections delegates InternalAPIException handling."""
    api_exception = privx_api.exceptions.InternalAPIException("500 Internal Server Error")
    mock_api.search_connections.side_effect = api_exception

    # Mock handle_http_5xx_error to re-raise so we can verify it was called
    mock_handle_http_5xx_error.side_effect = api_exception

    with pytest.raises(privx_api.exceptions.InternalAPIException):
        search_connections(mock_api)

    mock_handle_http_5xx_error.assert_called_once_with(api_exception, "search_connections")


@pytest.mark.unit
def test_search_connections_propagates_errors_when_requested(mock_api: MagicMock) -> None:
    api_exception = privx_api.exceptions.InternalAPIException("503 Service Unavailable", 503)
    mock_api.search_connections.side_effect = api_exception

    with pytest.raises(privx_api.exceptions.InternalAPIException):
        search_connections(mock_api, propagate_errors=True)
