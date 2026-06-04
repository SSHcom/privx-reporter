"""Tests for access_group API functions."""

from unittest.mock import MagicMock

import pytest

from lib.report_api.access_group import get_access_group_by_id


@pytest.mark.unit
def test_get_access_group_by_id_success(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_access_group_by_id correctly retrieves and returns an access group when found by its ID."""
    mock_response.data = {
        "id": "ag-123",
        "name": "Production Access",
        "description": "Access to production environment",
    }
    mock_api.get_access_group.return_value = mock_response

    result = get_access_group_by_id(mock_api, "ag-123")

    assert result is not None
    assert result["id"] == "ag-123"
    assert result["name"] == "Production Access"
    mock_api.get_access_group.assert_called_once_with("ag-123")


@pytest.mark.unit
def test_get_access_group_by_id_with_error_status(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_access_group_by_id returns None when API response indicates an error."""
    mock_response.ok = False
    mock_response.status = 404
    mock_response.data = {"details": {"error_code": "NOT_FOUND"}}
    mock_api.get_access_group.return_value = mock_response

    result = get_access_group_by_id(mock_api, "nonexistent")

    assert result is None


@pytest.mark.unit
def test_get_access_group_by_id_with_status_400_in_data(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that wrapper returns API data object even if it carries a status field."""
    mock_response.data = {
        "status": 400,
        "details": {"error_code": "BAD_REQUEST"},
    }
    mock_api.get_access_group.return_value = mock_response

    result = get_access_group_by_id(mock_api, "ag-123")

    assert result == mock_response.data
