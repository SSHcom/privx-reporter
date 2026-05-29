"""Tests for roles API functions."""

from unittest.mock import MagicMock

import pytest

from lib.report_api.roles import (
    get_role_by_id,
    get_role_by_name,
    get_role_members,
    get_roles,
    get_user_roles,
)

#### get_roles tests ####


@pytest.mark.unit
def test_get_roles_success(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_roles correctly retrieves and returns all roles from the API response items."""
    mock_response.data = {
        "count": 2,
        "items": [
            {"id": "role1", "name": "admin"},
            {"id": "role2", "name": "user"},
        ],
    }
    mock_api.get_roles.return_value = mock_response

    result = get_roles(mock_api)

    assert len(result) == 2
    assert result[0]["id"] == "role1"
    assert result[1]["name"] == "user"


@pytest.mark.unit
def test_get_roles_with_status_error(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_roles returns an empty list when response contains an error status."""
    mock_response.data = {
        "status": 500,
        "details": {"error_code": "SERVER_ERROR"},
    }
    mock_api.get_roles.return_value = mock_response

    result = get_roles(mock_api)

    assert result == []


@pytest.mark.unit
def test_get_roles_with_missing_items(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_roles returns an empty list when the response data is missing the items key."""
    mock_response.data = {}
    mock_api.get_roles.return_value = mock_response

    result = get_roles(mock_api)

    assert result == []


#### get_role_by_id tests ####


@pytest.mark.unit
def test_get_role_by_id_success(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_role_by_id correctly retrieves and returns a role when found by its ID."""
    mock_response.data = {"id": "role1", "name": "admin", "description": "Admin role"}
    mock_api.get_role.return_value = mock_response

    result = get_role_by_id(mock_api, "role1")

    assert result is not None
    assert result["id"] == "role1"
    assert result["name"] == "admin"
    mock_api.get_role.assert_called_once_with("role1")


@pytest.mark.unit
def test_get_role_by_id_with_error_status(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_role_by_id returns None when API response indicates an error."""
    mock_response.ok = False
    mock_response.status = 404
    mock_response.data = {"details": {"error_code": "NOT_FOUND"}}
    mock_api.get_role.return_value = mock_response

    result = get_role_by_id(mock_api, "nonexistent")

    assert result is None


#### get_role_by_name tests ####


@pytest.mark.unit
def test_get_role_by_name_success(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_role_by_name correctly finds and returns a role by matching its name from the roles list."""
    mock_response.data = {
        "count": 2,
        "items": [
            {"id": "role1", "name": "admin"},
            {"id": "role2", "name": "user"},
        ],
    }
    mock_api.get_roles.return_value = mock_response

    result = get_role_by_name(mock_api, "admin")

    assert result is not None
    assert result["id"] == "role1"
    assert result["name"] == "admin"


@pytest.mark.unit
def test_get_role_by_name_not_found(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_role_by_name returns None when no role with the specified name exists in the roles list."""
    mock_response.data = {
        "count": 2,
        "items": [
            {"id": "role1", "name": "admin"},
            {"id": "role2", "name": "user"},
        ],
    }
    mock_api.get_roles.return_value = mock_response

    result = get_role_by_name(mock_api, "nonexistent")

    assert result is None


@pytest.mark.unit
def test_get_role_by_name_when_no_roles(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_role_by_name returns None when there are no roles available to search."""
    mock_response.data = {"count": 0, "items": []}
    mock_api.get_roles.return_value = mock_response

    result = get_role_by_name(mock_api, "admin")

    assert result is None


#### get_role_members tests ####


@pytest.mark.unit
def test_get_role_members_success(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_role_members retrieves role members with default pagination."""
    mock_response.data = {
        "count": 2,
        "items": [
            {"id": "user1", "username": "alice"},
            {"id": "user2", "username": "bob"},
        ],
    }
    mock_api.get_role_members.return_value = mock_response

    result = get_role_members(mock_api, "role1")

    assert result["count"] == 2
    assert len(result["items"]) == 2
    mock_api.get_role_members.assert_called_once_with(role_id="role1", offset=0, limit=50)


@pytest.mark.unit
def test_get_role_members_with_custom_params(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_role_members correctly applies custom pagination parameters (limit and offset) when provided."""
    mock_response.data = {"count": 1, "items": [{"id": "user1"}]}
    mock_api.get_role_members.return_value = mock_response

    result = get_role_members(mock_api, "role1", limit=10, offset=20)

    assert result["count"] == 1
    mock_api.get_role_members.assert_called_once_with(role_id="role1", offset=20, limit=10)


@pytest.mark.unit
def test_get_role_members_with_not_found_status_returns_empty(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_role_members returns empty result when role is not found."""
    mock_response.ok = False
    mock_response.status = 404
    mock_response.data = {
        "details": {"error_code": "ROLE_NOT_FOUND"},
    }
    mock_api.get_role_members.return_value = mock_response

    result = get_role_members(mock_api, "deleted-role")

    assert result == {"count": 0, "items": []}


@pytest.mark.unit
def test_get_role_members_with_embedded_not_found_status_returns_empty(
    mock_api: MagicMock, mock_response: MagicMock
) -> None:
    """Test that get_role_members returns empty result when response payload has role-not-found status."""
    mock_response.ok = True
    mock_response.data = {
        "status": 404,
        "details": {"error_code": "ROLE_NOT_FOUND"},
    }
    mock_api.get_role_members.return_value = mock_response

    result = get_role_members(mock_api, "deleted-role")

    assert result == {"count": 0, "items": []}


@pytest.mark.unit
def test_get_role_members_with_invalid_response_raises_exception(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_role_members raises an exception when response data is invalid."""
    mock_response.data = {"count": None, "items": [{"id": "user1"}]}
    mock_api.get_role_members.return_value = mock_response

    with pytest.raises(Exception, match="Failed to get role members"):
        get_role_members(mock_api, "role1")


#### get_user_roles tests ####


@pytest.mark.unit
def test_get_user_roles_success(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_user_roles correctly retrieves and returns all roles assigned to a specific user."""
    mock_response.data = {
        "count": 2,
        "items": [
            {"id": "role1", "name": "admin"},
            {"id": "role2", "name": "user"},
        ],
    }
    mock_api.get_user_roles.return_value = mock_response

    result = get_user_roles(mock_api, "user1")

    assert len(result) == 2
    assert result[0]["id"] == "role1"
    mock_api.get_user_roles.assert_called_once_with("user1")


@pytest.mark.unit
def test_get_user_roles_with_status_error(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_user_roles returns empty list when user is not found (404 or 400 error)."""
    mock_response.ok = False
    mock_response.status = 404
    mock_response.data = {
        "details": {"error_code": "USER_NOT_FOUND"},
    }
    mock_api.get_user_roles.return_value = mock_response

    result = get_user_roles(mock_api, "nonexistent")
    assert result == []


@pytest.mark.unit
def test_get_user_roles_with_bad_request(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_user_roles returns empty list when user is not found (400 BAD_REQUEST error)."""
    mock_response.ok = False
    mock_response.status = 400
    mock_response.data = {
        "details": {"error_code": "BAD_REQUEST"},
    }
    mock_api.get_user_roles.return_value = mock_response

    result = get_user_roles(mock_api, "no-user")
    assert result == []


@pytest.mark.unit
def test_get_user_roles_with_missing_items(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_user_roles raises an exception when response data is missing items key."""
    mock_response.data = {}
    mock_api.get_user_roles.return_value = mock_response

    with pytest.raises(Exception, match="Failed to get user roles"):
        get_user_roles(mock_api, "user1")
