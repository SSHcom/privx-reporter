"""Tests for ui/db/user_queries.py."""

from unittest.mock import MagicMock, patch

import pytest

from ui.db import user_queries


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_list_users_returns_users_with_groups(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        (1, "admin", "Administrator", True, True, "admin"),
        (2, "user1", "User One", False, True, "users"),
    ]
    mock_result.keys.return_value = ["id", "name", "display_name", "is_admin", "has_profile", "group_name"]
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    result = user_queries.list_users()

    assert len(result) == 2
    assert result[0]["name"] == "admin"
    assert result[0]["group_name"] == "admin"
    assert result[1]["name"] == "user1"
    assert result[1]["group_name"] == "users"


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_get_user_returns_user_with_group_id(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.fetchone.return_value = (1, "testuser", "Test User", False, True, 2, "users")
    mock_result.keys.return_value = [
        "id",
        "name",
        "display_name",
        "is_admin",
        "has_profile",
        "user_group_id",
        "group_name",
    ]
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    result = user_queries.get_user(1)

    assert result is not None
    assert result["name"] == "testuser"
    assert result["user_group_id"] == 2
    assert result["group_name"] == "users"


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_get_user_returns_none_when_not_found(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    result = user_queries.get_user(999)

    assert result is None


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_update_user_profile_rejects_same_password(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    current_hash = user_queries.hash_password("SamePass!")
    mock_existing_password_result = MagicMock()
    mock_existing_password_result.scalar_one_or_none.return_value = current_hash
    mock_db.connection.execute.return_value = mock_existing_password_result
    mock_use_database.return_value = mock_db

    success, message = user_queries.update_user_profile(user_id=1, password="SamePass!")

    assert success is False
    assert "different from current password" in message.lower()
    assert mock_db.connection.execute.call_count == 1


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_update_user_profile_updates_when_password_is_new(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    current_hash = user_queries.hash_password("OldPass!")
    mock_existing_password_result = MagicMock()
    mock_existing_password_result.scalar_one_or_none.return_value = current_hash

    mock_update_result = MagicMock()
    mock_update_result.rowcount = 1

    mock_db.connection.execute.side_effect = [mock_existing_password_result, mock_update_result]
    mock_use_database.return_value = mock_db

    success, message = user_queries.update_user_profile(user_id=1, password="NewPass!")

    assert success is True
    assert "profile updated successfully" in message.lower()
    assert mock_db.connection.execute.call_count == 2


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_update_user_profile_password_returns_not_found_when_user_missing(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_existing_password_result = MagicMock()
    mock_existing_password_result.scalar_one_or_none.return_value = None
    mock_db.connection.execute.return_value = mock_existing_password_result
    mock_use_database.return_value = mock_db

    success, message = user_queries.update_user_profile(user_id=999, password="NewPass!")

    assert success is False
    assert "not found" in message.lower()
    assert mock_db.connection.execute.call_count == 1


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_update_user_profile_rejects_password_policy_violation(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_use_database.return_value = mock_db

    success, message = user_queries.update_user_profile(user_id=1, password="short!")

    assert success is False
    assert "at least 8 characters" in message.lower()
    mock_db.connection.execute.assert_not_called()


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_create_user_rejects_password_policy_violation(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_use_database.return_value = mock_db

    success, message = user_queries.create_user(
        name="new-user",
        display_name="New User",
        user_group_id=2,
        password="NoSpecial8",
        has_profile=True,
    )

    assert success is False
    assert "special character" in message.lower()
    mock_db.connection.execute.assert_not_called()


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_update_user_user_group_success(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    # Mock successful update (rowcount = 1)
    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    success, message = user_queries.update_user_user_group(user_id=1, user_group_id=3)

    assert success is True
    assert "successfully" in message.lower()


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_update_user_user_group_to_admin_enables_profile_access(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_group_result = MagicMock()
    mock_group_result.scalar_one_or_none.return_value = "admin"
    mock_update_result = MagicMock()
    mock_update_result.rowcount = 1
    mock_db.connection.execute.side_effect = [mock_group_result, mock_update_result]
    mock_use_database.return_value = mock_db

    success, message = user_queries.update_user_user_group(user_id=1, user_group_id=1)

    assert success is True
    assert "successfully" in message.lower()
    update_stmt = mock_db.connection.execute.call_args_list[1].args[0]
    assert "has_profile" in str(update_stmt)


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_update_user_user_group_non_admin_keeps_profile_access_unchanged(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_group_result = MagicMock()
    mock_group_result.scalar_one_or_none.return_value = "users"
    mock_update_result = MagicMock()
    mock_update_result.rowcount = 1
    mock_db.connection.execute.side_effect = [mock_group_result, mock_update_result]
    mock_use_database.return_value = mock_db

    success, message = user_queries.update_user_user_group(user_id=1, user_group_id=2)

    assert success is True
    assert "successfully" in message.lower()
    update_stmt = mock_db.connection.execute.call_args_list[1].args[0]
    assert "has_profile" not in str(update_stmt)


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_update_user_user_group_group_not_found(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_group_result = MagicMock()
    mock_group_result.scalar_one_or_none.return_value = None
    mock_db.connection.execute.return_value = mock_group_result
    mock_use_database.return_value = mock_db

    success, message = user_queries.update_user_user_group(user_id=1, user_group_id=999)

    assert success is False
    assert "user group" in message.lower()
    assert "not found" in message.lower()


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_update_user_user_group_user_not_found(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    # Mock existing group lookup followed by user-not-found update.
    mock_group_result = MagicMock()
    mock_group_result.scalar_one_or_none.return_value = "users"
    mock_result = MagicMock()
    mock_result.rowcount = 0
    mock_db.connection.execute.side_effect = [mock_group_result, mock_result]
    mock_use_database.return_value = mock_db

    success, message = user_queries.update_user_user_group(user_id=999, user_group_id=3)

    assert success is False
    assert "not found" in message.lower()


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_update_user_user_group_handles_exception(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(side_effect=Exception("DB error"))
    mock_use_database.return_value = mock_db

    success, message = user_queries.update_user_user_group(user_id=1, user_group_id=3)

    assert success is False
    assert "failed" in message.lower()


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_update_user_has_profile_success(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    success, message = user_queries.update_user_has_profile(user_id=1, has_profile=False)

    assert success is True
    assert "successfully" in message.lower()


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_update_user_has_profile_user_not_found(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.rowcount = 0
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    success, message = user_queries.update_user_has_profile(user_id=999, has_profile=False)

    assert success is False
    assert "not found" in message.lower()


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_update_user_has_profile_handles_exception(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(side_effect=Exception("DB error"))
    mock_use_database.return_value = mock_db

    success, message = user_queries.update_user_has_profile(user_id=1, has_profile=True)

    assert success is False
    assert "failed" in message.lower()


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_get_user_for_login_returns_user_with_password(mock_use_database: MagicMock) -> None:
    """Test that get_user_for_login includes encrypted_password field."""
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.fetchone.return_value = (
        1,
        "testuser",
        "Test User",
        False,
        True,
        2,
        "$2b$12$hashedpassword",
        "users",
    )
    mock_result.keys.return_value = [
        "id",
        "name",
        "display_name",
        "is_admin",
        "has_profile",
        "user_group_id",
        "encrypted_password",
        "group_name",
    ]
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    result = user_queries.get_user_for_login("testuser")

    assert result is not None
    assert result["name"] == "testuser"
    assert result["user_group_id"] == 2
    assert result["encrypted_password"] == "$2b$12$hashedpassword"
    assert result["group_name"] == "users"


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_delete_user_success(mock_use_database: MagicMock) -> None:
    """Test that delete_user returns (True, ...) when a row is deleted."""
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    success, message = user_queries.delete_user(1)

    assert success is True
    assert "deleted" in message.lower()


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_delete_user_not_found(mock_use_database: MagicMock) -> None:
    """Test that delete_user returns (False, ...) when no row is deleted."""
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.rowcount = 0
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    success, message = user_queries.delete_user(999)

    assert success is False
    assert "not found" in message.lower()


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_delete_user_integrity_error(mock_use_database: MagicMock) -> None:
    """Test that delete_user returns (False, ...) on IntegrityError."""
    from sqlalchemy.exc import IntegrityError

    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(side_effect=IntegrityError("stmt", {}, Exception("fk")))
    mock_use_database.return_value = mock_db

    success, message = user_queries.delete_user(1)

    assert success is False
    assert "cannot delete" in message.lower()


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_get_user_for_login_returns_none_when_not_found(mock_use_database: MagicMock) -> None:
    """Test that get_user_for_login returns None for unknown user."""
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    result = user_queries.get_user_for_login("nonexistent")

    assert result is None


@pytest.mark.unit
@patch("ui.db.user_queries.use_database")
def test_create_oidc_user_sets_oidc_password_marker(mock_use_database: MagicMock) -> None:
    """Test that create_oidc_user stores the fixed OIDC password marker."""
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)
    mock_use_database.return_value = mock_db

    success, message = user_queries.create_oidc_user("oidc_user", "OIDC User", 2)

    assert success is True
    assert "created successfully" in message.lower()
    payload = mock_db.connection.execute.call_args.args[1]
    assert payload["encrypted_password"] == user_queries.OIDC_ENCRYPTED_PASSWORD_MARKER
