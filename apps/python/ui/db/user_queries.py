"""Database queries for user management."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from lib.clients.postgresql import use_database
from lib.database.models.admin.user import UserTable
from lib.database.models.admin.user_group import UserGroupTable
from ui.utils.password import hash_password, validate_password, validate_password_policy

OIDC_ENCRYPTED_PASSWORD_MARKER = "OIDC"


def list_users() -> list[dict[str, Any]]:
    """Return all users joined with their group name.

    Returns:
        A list of dictionaries with user data including group name.
    """
    db = use_database("admin")

    with db.connection.begin():
        result = db.connection.execute(
            select(
                UserTable.c.id,
                UserTable.c.name,
                UserTable.c.display_name,
                UserTable.c.is_admin,
                UserTable.c.has_profile,
                UserGroupTable.c.name.label("group_name"),
            )
            .select_from(UserTable)
            .join(UserGroupTable, UserTable.c.user_group_id == UserGroupTable.c.id)
            .order_by(UserTable.c.name)
        )

        rows = result.fetchall()
        columns = result.keys()

        return [dict(zip(columns, row)) for row in rows]


def get_user(user_id: int) -> dict[str, Any] | None:
    """Get a single user by ID.

    Args:
        user_id: The user ID to look up.

    Returns:
        A dictionary with user data, or None if not found.
    """
    db = use_database("admin")

    with db.connection.begin():
        result = db.connection.execute(
            select(
                UserTable.c.id,
                UserTable.c.name,
                UserTable.c.display_name,
                UserTable.c.is_admin,
                UserTable.c.has_profile,
                UserTable.c.user_group_id,
                UserGroupTable.c.name.label("group_name"),
            )
            .select_from(UserTable)
            .join(UserGroupTable, UserTable.c.user_group_id == UserGroupTable.c.id)
            .where(UserTable.c.id == user_id)
        )

        row = result.fetchone()
        if row is None:
            return None

        columns = result.keys()
        return dict(zip(columns, row))


def get_user_by_name(name: str) -> dict[str, Any] | None:
    """Get a single user by username.

    Args:
        name: The username to look up.

    Returns:
        A dictionary with user data, or None if not found.
    """
    db = use_database("admin")

    with db.connection.begin():
        result = db.connection.execute(
            select(
                UserTable.c.id,
                UserTable.c.name,
                UserTable.c.display_name,
                UserTable.c.is_admin,
                UserTable.c.has_profile,
                UserGroupTable.c.name.label("group_name"),
            )
            .select_from(UserTable)
            .join(UserGroupTable, UserTable.c.user_group_id == UserGroupTable.c.id)
            .where(UserTable.c.name == name)
        )

        row = result.fetchone()
        if row is None:
            return None

        columns = result.keys()
        return dict(zip(columns, row))


def get_user_for_login(name: str) -> dict[str, Any] | None:
    """Get a user by username for login verification.

    Includes encrypted_password for authentication. This function is
    query-only - password comparison should be done by the caller.

    Args:
        name: The username to look up.

    Returns:
        A dictionary with user data including encrypted_password,
        or None if not found.
    """
    db = use_database("admin")

    with db.connection.begin():
        result = db.connection.execute(
            select(
                UserTable.c.id,
                UserTable.c.name,
                UserTable.c.display_name,
                UserTable.c.is_admin,
                UserTable.c.has_profile,
                UserTable.c.user_group_id,
                UserTable.c.encrypted_password,
                UserGroupTable.c.name.label("group_name"),
            )
            .select_from(UserTable)
            .join(UserGroupTable, UserTable.c.user_group_id == UserGroupTable.c.id)
            .where(UserTable.c.name == name)
        )

        row = result.fetchone()
        if row is None:
            return None

        columns = result.keys()
        return dict(zip(columns, row))


def create_user(
    name: str,
    display_name: str,
    user_group_id: int,
    password: str,
    has_profile: bool = True,
) -> tuple[bool, str]:
    """Create a new user with a hashed password.

    Args:
        name: The unique username.
        display_name: The display name for the user.
        user_group_id: The ID of the user group to assign.
        password: The plain text password (will be hashed).
        has_profile: If True, user can edit their profile (display name, password).

    Returns:
        A tuple of (success, message) where success is True if the user was created,
        and message contains a success or error description.
    """
    db = use_database("admin")

    try:
        policy_ok, policy_error = validate_password_policy(password)
        if not policy_ok:
            return False, policy_error
        password_hash = hash_password(password)

        with db.connection.begin():
            db.connection.execute(
                insert(UserTable),
                {
                    "is_admin": False,
                    "has_profile": has_profile,
                    "name": name,
                    "display_name": display_name,
                    "user_group_id": user_group_id,
                    "encrypted_password": password_hash,
                },
            )

        return True, f"User '{name}' created successfully."

    except IntegrityError:
        return False, f"Username '{name}' is already taken."
    except Exception as e:
        return False, f"Failed to create user: {e}"


def create_oidc_user(
    name: str,
    display_name: str,
    user_group_id: int,
    has_profile: bool = True,
) -> tuple[bool, str]:
    """Create a new OIDC-only user with a non-local password marker."""
    db = use_database("admin")

    try:
        with db.connection.begin():
            db.connection.execute(
                insert(UserTable),
                {
                    "is_admin": False,
                    "has_profile": has_profile,
                    "name": name,
                    "display_name": display_name,
                    "user_group_id": user_group_id,
                    "encrypted_password": OIDC_ENCRYPTED_PASSWORD_MARKER,
                },
            )

        return True, f"User '{name}' created successfully."

    except IntegrityError:
        return False, f"Username '{name}' is already taken."
    except Exception as e:
        return False, f"Failed to create user: {e}"


def update_user_profile(
    user_id: int,
    display_name: str | None = None,
    password: str | None = None,
) -> tuple[bool, str]:
    """Update a user's display name and/or password.

    Args:
        user_id: The ID of the user to update.
        display_name: The new display name (optional).
        password: The new plain text password (optional, will be hashed).

    Returns:
        A tuple of (success, message) where success is True if the update succeeded,
        and message contains a success or error description.
    """
    if display_name is None and password is None:
        return False, "No changes specified."

    db = use_database("admin")

    try:
        with db.connection.begin():
            updates = {}

            if display_name is not None:
                updates["display_name"] = display_name

            if password is not None:
                policy_ok, policy_error = validate_password_policy(password)
                if not policy_ok:
                    return False, policy_error
                existing_password_hash = db.connection.execute(
                    select(UserTable.c.encrypted_password).where(UserTable.c.id == user_id)
                ).scalar_one_or_none()
                if existing_password_hash is None:
                    return False, f"User with ID {user_id} not found."
                if validate_password(password, str(existing_password_hash)):
                    return False, "New password must be different from current password."
                updates["encrypted_password"] = hash_password(password)

            result = db.connection.execute(update(UserTable).where(UserTable.c.id == user_id).values(**updates))

            if result.rowcount == 0:
                return False, f"User with ID {user_id} not found."

        return True, "Profile updated successfully."

    except Exception as e:
        return False, f"Failed to update profile: {e}"


def delete_user(user_id: int) -> tuple[bool, str]:
    """Delete a user by ID.

    Args:
        user_id: The ID of the user to delete.

    Returns:
        A tuple of (success, message) where success is True if the user was deleted,
        and message contains a success or error description.
    """
    db = use_database("admin")

    try:
        with db.connection.begin():
            result = db.connection.execute(delete(UserTable).where(UserTable.c.id == user_id))

            if result.rowcount == 0:
                return False, "User not found."

        return True, "User deleted successfully."

    except IntegrityError:
        return False, "Cannot delete user: they are referenced by other records."
    except Exception as e:
        return False, f"Failed to delete user: {e}"


def update_user_user_group(user_id: int, user_group_id: int) -> tuple[bool, str]:
    """Update a user's user group.

    Args:
        user_id: The ID of the user to update.
        user_group_id: The ID of the new user group.

    Returns:
        A tuple of (success, message) where success is True if the update succeeded,
        and message contains a success or error description.
    """
    db = use_database("admin")

    try:
        with db.connection.begin():
            target_group_name = db.connection.execute(
                select(UserGroupTable.c.name).where(UserGroupTable.c.id == user_group_id)
            ).scalar_one_or_none()

            if target_group_name is None:
                return False, f"User group with ID {user_group_id} not found."

            updates: dict[str, Any] = {"user_group_id": user_group_id}
            if str(target_group_name).strip().lower() == "admin":
                # Admin-group users must always retain profile edit access.
                updates["has_profile"] = True

            result = db.connection.execute(update(UserTable).where(UserTable.c.id == user_id).values(**updates))

            if result.rowcount == 0:
                return False, f"User with ID {user_id} not found."

        return True, "User group updated successfully."

    except Exception as e:
        return False, f"Failed to update user group: {e}"


def update_user_has_profile(user_id: int, has_profile: bool) -> tuple[bool, str]:
    """Update whether a user can edit their own profile.

    Args:
        user_id: The ID of the user to update.
        has_profile: True to allow profile editing, False to disable it.

    Returns:
        A tuple of (success, message) where success is True if the update succeeded,
        and message contains a success or error description.
    """
    db = use_database("admin")

    try:
        with db.connection.begin():
            result = db.connection.execute(
                update(UserTable).where(UserTable.c.id == user_id).values(has_profile=has_profile)
            )

            if result.rowcount == 0:
                return False, f"User with ID {user_id} not found."

        return True, "Profile access updated successfully."

    except Exception as e:
        return False, f"Failed to update profile access: {e}"
