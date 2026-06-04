"""Tests for hosts API functions."""

from unittest.mock import MagicMock

import pytest

from lib.report_api.hosts import get_host, search_hosts


@pytest.mark.unit
def test_search_hosts_success(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that search_hosts correctly retrieves and returns host search results with count and items."""
    mock_response.data = {
        "count": 2,
        "items": [
            {"id": "host1", "name": "server-01"},
            {"id": "host2", "name": "server-02"},
        ],
    }
    mock_api.search_hosts.return_value = mock_response

    search_payload = {"role": ["role-id-123"]}
    result = search_hosts(mock_api, search_payload)

    assert result["count"] == 2
    assert len(result["items"]) == 2
    mock_api.search_hosts.assert_called_once_with(search_payload=search_payload)


@pytest.mark.unit
def test_search_hosts_with_resp_not_ok(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that search_hosts returns None when the API response indicates an error (response.ok is False)."""
    mock_response.ok = False
    mock_response.status = 500
    mock_response.data = {"details": {"error_code": "INTERNAL_ERROR"}}
    mock_api.search_hosts.return_value = mock_response

    result = search_hosts(mock_api, {"role": ["role-id-123"]})

    assert result is None


@pytest.mark.unit
def test_search_hosts_with_status_400_in_data(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that search_hosts returns None when response data contains an error status code (>= 400)."""
    mock_response.data = {
        "status": 400,
        "details": {"error_code": "BAD_REQUEST"},
    }
    mock_api.search_hosts.return_value = mock_response

    result = search_hosts(mock_api, {"role": ["role-id-123"]})

    assert result is None


#### get_host tests ####


@pytest.mark.unit
def test_get_host_success(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_host correctly retrieves and returns a single host by ID with all host details."""
    mock_response.data = {
        "id": "host-123",
        "common_name": "server-01",
        "addresses": ["192.168.1.10"],
        "principals": [{"principal": "root"}],
    }
    mock_api.get_host.return_value = mock_response

    result = get_host(mock_api, "host-123")

    assert result["id"] == "host-123"
    assert result["common_name"] == "server-01"
    mock_api.get_host.assert_called_once_with(host_id="host-123")


@pytest.mark.unit
def test_get_host_with_error_raises_exception(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_host raises an exception when API response indicates an error."""
    mock_response.ok = False
    mock_response.status = 404
    mock_response.data = {"details": {"error_code": "NOT_FOUND"}}
    mock_api.get_host.return_value = mock_response

    with pytest.raises(Exception, match="Failed to get host"):
        get_host(mock_api, "nonexistent-host")
