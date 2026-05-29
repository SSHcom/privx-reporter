"""User permissions data class and session permission checks."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from ui.services.session import keys


@dataclass(frozen=True)
class UserPermissions:
    """Resolved permissions for an authenticated user."""

    group: str
    display_name: str

    @property
    def is_admin(self) -> bool:
        """Return *True* if the user belongs to the ``admin`` group."""
        return self.group == "admin"


def is_admin() -> bool:
    """Return True if the current session user has admin permissions."""
    permissions = st.session_state.get(keys.USER_PERMISSIONS)
    if not isinstance(permissions, UserPermissions):
        return False
    return permissions.is_admin


def is_superadmin_username(username: str | None) -> bool:
    """Return True when username is the superadmin account."""
    return str(username or "").strip().lower() == "admin"


def is_protected_group_name(group_name: str | None) -> bool:
    """Return True when the user group name is protected from deletion."""
    return str(group_name or "").strip().lower() == "admin"


def can_edit_profile(user_id: int, *, target_username: str | None = None) -> bool:
    """Check if the current session user can edit the specified user's profile.

    Admin users can edit any profile.
    Non-admin users can only edit their own profile.
    The superadmin account can only be edited by the superadmin user.
    """
    current_username = st.session_state.get(keys.USERNAME)
    if is_superadmin_username(target_username) and not is_superadmin_username(current_username):
        return False

    current_user_id = st.session_state.get(keys.USER_ID)
    return is_admin() or current_user_id == user_id
