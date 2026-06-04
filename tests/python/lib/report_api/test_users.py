"""Tests for users API functions."""

from unittest.mock import MagicMock

import pytest

from lib.report_api.users import get_user_by_id, get_users, search_users

#### get_user_by_id tests ####


@pytest.mark.unit
def test_get_user_by_id_success(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_user_by_id correctly retrieves and returns a user when found by its ID."""
    mock_response.data = {
        "id": "user-123",
        "username": "john.doe",
        "email": "john.doe@example.com",
        "full_name": "John Doe",
    }
    mock_api.get_user.return_value = mock_response

    result = get_user_by_id(mock_api, "user-123")

    assert result is not None
    assert result["id"] == "user-123"
    assert result["username"] == "john.doe"
    mock_api.get_user.assert_called_once_with("user-123")


@pytest.mark.unit
def test_get_user_by_id_with_error_status(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_user_by_id returns None when API response indicates an error."""
    mock_response.ok = False
    mock_response.status = 404
    mock_response.data = {"details": {"error_code": "NOT_FOUND"}}
    mock_api.get_user.return_value = mock_response

    result = get_user_by_id(mock_api, "nonexistent")

    assert result is None


@pytest.mark.unit
def test_get_user_by_id_with_status_400_in_data(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_user_by_id returns None when response data contains an error status code (>= 400)."""
    mock_response.data = {
        "status": 400,
        "details": {"error_code": "BAD_REQUEST"},
    }
    mock_api.get_user.return_value = mock_response

    result = get_user_by_id(mock_api, "user-123")

    assert result is None


#### get_users tests ####


@pytest.mark.unit
def test_get_users_success(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_users correctly retrieves and returns all users with default pagination."""
    mock_response.data = {
        "count": 2,
        "items": [
            {"id": "user1", "username": "alice"},
            {"id": "user2", "username": "bob"},
        ],
    }
    mock_api.get_users.return_value = mock_response

    result = get_users(mock_api)

    assert result["count"] == 2
    assert len(result["items"]) == 2
    mock_api.get_users.assert_called_once_with(offset=0, limit=100)


@pytest.mark.unit
def test_get_users_with_custom_params(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_users correctly applies custom pagination parameters (limit and offset) when provided."""
    mock_response.data = {"count": 1, "items": [{"id": "user1"}]}
    mock_api.get_users.return_value = mock_response

    result = get_users(mock_api, offset=20, limit=10)

    assert result["count"] == 1
    mock_api.get_users.assert_called_once_with(offset=20, limit=10)


@pytest.mark.unit
def test_get_users_with_error_status(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_users returns None when API response indicates an error."""
    mock_response.ok = False
    mock_response.status = 500
    mock_response.data = {"details": {"error_code": "INTERNAL_ERROR"}}
    mock_api.get_users.return_value = mock_response

    result = get_users(mock_api)

    assert result is None


#### search_users tests ####


@pytest.mark.unit
def test_search_users_success(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that search_users correctly retrieves and returns user search results with count and items."""
    mock_response.data = {
        "count": 2,
        "items": [
            {"id": "user1", "username": "alice", "email": "alice@example.com"},
            {"id": "user2", "username": "bob", "email": "bob@example.com"},
        ],
    }
    mock_api.search_users.return_value = mock_response

    search_payload = {"keywords": "alice"}
    result = search_users(mock_api, search_payload)

    assert result["count"] == 2
    assert len(result["items"]) == 2
    mock_api.search_users.assert_called_once_with(search_payload=search_payload)


@pytest.mark.unit
def test_search_users_with_resp_not_ok(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that search_users returns None when the API response indicates an error (response.ok is False)."""
    mock_response.ok = False
    mock_response.status = 500
    mock_response.data = {"details": {"error_code": "INTERNAL_ERROR"}}
    mock_api.search_users.return_value = mock_response

    result = search_users(mock_api, {"keywords": "test"})

    assert result is None


@pytest.mark.unit
def test_search_users_with_status_400_in_data(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that search_users returns None when response data contains an error status code (>= 400)."""
    mock_response.data = {
        "status": 400,
        "details": {"error_code": "BAD_REQUEST"},
    }
    mock_api.search_users.return_value = mock_response

    result = search_users(mock_api, {"keywords": "test"})

    assert result is None


@pytest.mark.unit
def test_search_users_with_empty_results(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that search_users correctly handles empty search results."""
    mock_response.data = {
        "count": 0,
        "items": [],
    }
    mock_api.search_users.return_value = mock_response

    result = search_users(mock_api, {"keywords": "nonexistent"})

    assert result["count"] == 0
    assert len(result["items"]) == 0
