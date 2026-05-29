"""Tests for delete-user behavior in the Admin_User_Profile page.

These tests verify the dialog helper logic and delete section guards by
importing the page module with all Streamlit and DB dependencies fully
mocked at the sys.modules level.
"""

from __future__ import annotations

import sys
import types
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable


def _noop_dialog(title: str) -> Callable[[Callable[..., object]], Callable[..., object]]:
    """Pass-through decorator that strips the @st.dialog wrapper."""

    def decorator(fn: Callable[..., object]) -> Callable[..., object]:
        return fn

    return decorator


def _make_streamlit_stub(session_state: dict) -> types.ModuleType:
    """Build a minimal streamlit stub module for page import."""
    st = types.ModuleType("streamlit")
    st.session_state = session_state  # type: ignore[attr-defined]
    st.dialog = _noop_dialog  # type: ignore[attr-defined]
    st.query_params = {}  # type: ignore[attr-defined]
    for attr in (
        "set_page_config",
        "markdown",
        "stop",
        "title",
        "warning",
        "caption",
        "rerun",
        "error",
        "success",
        "info",
        "expander",
        "form",
        "text_input",
        "form_submit_button",
        "write",
        "checkbox",
        "subheader",
        "divider",
        "switch_page",
    ):
        setattr(st, attr, MagicMock())
    st.button = MagicMock(return_value=False)  # type: ignore[attr-defined]
    st.columns = MagicMock(return_value=[MagicMock(), MagicMock()])  # type: ignore[attr-defined]
    st.selectbox = MagicMock(return_value="users")  # type: ignore[attr-defined]
    return st


def _load_page_module(
    st_stub: types.ModuleType,
    session_state: dict,
    *,
    user: dict | None = None,
    is_admin_value: bool = True,
    can_edit_profile_value: bool = True,
    delete_user_result: tuple[bool, str] = (True, "User deleted successfully."),
) -> types.ModuleType:
    """Load Admin_User_Profile with all external dependencies mocked."""
    for key in list(sys.modules.keys()):
        if "Admin_User_Profile" in key:
            del sys.modules[key]

    default_user = {
        "id": 2,
        "name": "targetuser",
        "display_name": "Target User",
        "is_admin": False,
        "has_profile": True,
        "user_group_id": 2,
        "group_name": "users",
    }
    resolved_user = user if user is not None else default_user

    mock_get_user = MagicMock(return_value=resolved_user)
    mock_delete_user = MagicMock(return_value=delete_user_result)
    mock_update_profile = MagicMock(return_value=(True, "Profile updated successfully."))
    mock_update_group = MagicMock(return_value=(True, "User group updated successfully."))
    mock_update_has_profile = MagicMock(return_value=(True, "Profile access updated successfully."))
    mock_list_user_groups = MagicMock(return_value=[{"id": 1, "name": "admin"}, {"id": 2, "name": "users"}])
    mock_is_admin = MagicMock(return_value=is_admin_value)
    mock_can_edit_profile = MagicMock(return_value=can_edit_profile_value)
    mock_setup_page = MagicMock()
    mock_render_sidebar = MagicMock()

    uq_mod = types.ModuleType("ui.db.user_queries")
    uq_mod.get_user = mock_get_user  # type: ignore[attr-defined]
    uq_mod.delete_user = mock_delete_user  # type: ignore[attr-defined]
    uq_mod.update_user_profile = mock_update_profile  # type: ignore[attr-defined]
    uq_mod.update_user_user_group = mock_update_group  # type: ignore[attr-defined]
    uq_mod.update_user_has_profile = mock_update_has_profile  # type: ignore[attr-defined]

    ug_mod = types.ModuleType("ui.db.user_group_queries")
    ug_mod.list_user_groups = mock_list_user_groups  # type: ignore[attr-defined]

    perm_mod = types.ModuleType("ui.services.permissions")
    perm_mod.is_admin = mock_is_admin  # type: ignore[attr-defined]
    perm_mod.can_edit_profile = mock_can_edit_profile  # type: ignore[attr-defined]

    sk_mod = types.ModuleType("ui.services.session.keys")
    sk_mod.USER_ID = "user_id"  # type: ignore[attr-defined]
    sk_mod.USERNAME = "username"  # type: ignore[attr-defined]
    sk_mod.HAS_PROFILE = "has_profile"  # type: ignore[attr-defined]

    sb_mod = types.ModuleType("ui.components.sidebar")
    sb_mod.render_sidebar = mock_render_sidebar  # type: ignore[attr-defined]

    pb_mod = types.ModuleType("ui.services.page_bootstrap")
    pb_mod.setup_page = mock_setup_page  # type: ignore[attr-defined]

    const_mod = types.ModuleType("ui.constants")
    const_mod.USER_PROFILE_PAGE_TITLE = "User Profile"  # type: ignore[attr-defined]
    const_mod.PAGE_STYLE = ""  # type: ignore[attr-defined]

    # Seed session state with a user_id so the page resolves the user
    session_state.setdefault("_profile_user_id", "2")
    session_state.setdefault("user_id", 2)
    session_state.setdefault("has_profile", True)

    overrides = {
        "streamlit": st_stub,
        "ui.db.user_queries": uq_mod,
        "ui.db.user_group_queries": ug_mod,
        "ui.services.permissions": perm_mod,
        "ui.services.page_bootstrap": pb_mod,
        "ui.services.session.keys": sk_mod,
        "ui.components.sidebar": sb_mod,
        "ui.constants": const_mod,
    }

    with patch.dict(sys.modules, overrides):
        import importlib
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "ui.pages.Admin_User_Profile",
            "ui/pages/Admin_User_Profile.py",
        )
        page_module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        sys.modules["ui.pages.Admin_User_Profile"] = page_module
        spec.loader.exec_module(page_module)  # type: ignore[union-attr]
        page_module._mock_delete_user = mock_delete_user  # type: ignore[attr-defined]
        page_module._mock_update_has_profile = mock_update_has_profile  # type: ignore[attr-defined]
        return page_module


# ---------------------------------------------------------------------------
# Dialog tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_delete_dialog_confirm_success_stores_result_and_switches_page() -> None:
    """Confirming deletion on success stores result and calls switch_page."""
    session_state: dict = {"username": "admin"}
    st_stub = _make_streamlit_stub(session_state)
    page = _load_page_module(st_stub, session_state, delete_user_result=(True, "User deleted successfully."))

    call_count = [0]

    def mock_button(label: str, **kwargs: object) -> bool:
        call_count[0] += 1
        return call_count[0] == 1  # Only "Delete" button clicked

    st_stub.button.side_effect = mock_button

    page._confirm_delete_user_dialog(user_id=2, username="targetuser")

    page._mock_delete_user.assert_called_once_with(2)
    assert session_state.get("delete_user_result") == (True, "User deleted successfully.")
    st_stub.switch_page.assert_called_once_with("pages/Admin_Users.py")


@pytest.mark.unit
def test_delete_dialog_confirm_failure_stores_result_and_reruns() -> None:
    """Confirming deletion on failure stores error result and reruns (no redirect)."""
    session_state: dict = {"username": "admin"}
    st_stub = _make_streamlit_stub(session_state)
    page = _load_page_module(
        st_stub,
        session_state,
        delete_user_result=(False, "Cannot delete user: they are referenced by other records."),
    )

    call_count = [0]

    def mock_button(label: str, **kwargs: object) -> bool:
        call_count[0] += 1
        return call_count[0] == 1

    st_stub.button.side_effect = mock_button

    page._confirm_delete_user_dialog(user_id=2, username="targetuser")

    page._mock_delete_user.assert_called_once_with(2)
    success, message = session_state["delete_user_result"]
    assert success is False
    assert "cannot delete" in message.lower()
    st_stub.switch_page.assert_not_called()
    st_stub.rerun.assert_called()


@pytest.mark.unit
def test_delete_dialog_cancel_does_not_call_delete() -> None:
    """Pressing Cancel does not invoke delete_user."""
    session_state: dict = {"username": "admin"}
    st_stub = _make_streamlit_stub(session_state)
    page = _load_page_module(st_stub, session_state)

    call_count = [0]

    def mock_button(label: str, **kwargs: object) -> bool:
        call_count[0] += 1
        return call_count[0] == 2  # Cancel button (second) clicked

    st_stub.button.side_effect = mock_button

    page._confirm_delete_user_dialog(user_id=2, username="targetuser")

    page._mock_delete_user.assert_not_called()
    assert "delete_user_result" not in session_state


# ---------------------------------------------------------------------------
# Page-level guard tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_non_admin_does_not_see_delete_section() -> None:
    """Non-admin users should not see the delete button."""
    session_state: dict = {"username": "regularuser", "_profile_user_id": "2", "user_id": 2}
    st_stub = _make_streamlit_stub(session_state)
    _load_page_module(st_stub, session_state, is_admin_value=False)

    # button should never be called with "Delete User" label
    delete_calls = [call for call in st_stub.button.call_args_list if call.args and call.args[0] == "Delete User"]
    assert len(delete_calls) == 0


@pytest.mark.unit
def test_admin_sees_delete_button_for_regular_user() -> None:
    """Admin viewing a non-admin user's profile sees the Delete User button."""
    session_state: dict = {"username": "admin", "_profile_user_id": "2", "user_id": 2}
    st_stub = _make_streamlit_stub(session_state)
    _load_page_module(st_stub, session_state, is_admin_value=True)

    delete_calls = [call for call in st_stub.button.call_args_list if call.args and call.args[0] == "Delete User"]
    assert len(delete_calls) == 1


@pytest.mark.unit
def test_self_deletion_guard_shows_info_not_button() -> None:
    """Admin viewing their own profile sees an info message, not the delete button."""
    session_state: dict = {"username": "admin", "_profile_user_id": "1", "user_id": 1}
    st_stub = _make_streamlit_stub(session_state)
    own_user = {
        "id": 1,
        "name": "admin",
        "display_name": "Admin",
        "is_admin": True,
        "has_profile": True,
        "user_group_id": 1,
        "group_name": "admin",
    }
    _load_page_module(st_stub, session_state, user=own_user, is_admin_value=True)

    delete_calls = [call for call in st_stub.button.call_args_list if call.args and call.args[0] == "Delete User"]
    assert len(delete_calls) == 0
    # An info message should have been shown
    st_stub.info.assert_called()


@pytest.mark.unit
def test_admin_group_guard_blocks_non_admin_username() -> None:
    """Admin whose username is not 'admin' cannot delete another admin-group user."""
    session_state: dict = {"username": "otheradmin", "_profile_user_id": "3", "user_id": 3}
    st_stub = _make_streamlit_stub(session_state)
    target_admin_user = {
        "id": 3,
        "name": "anotheradmin",
        "display_name": "Another Admin",
        "is_admin": True,
        "has_profile": True,
        "user_group_id": 1,
        "group_name": "admin",
    }
    _load_page_module(st_stub, session_state, user=target_admin_user, is_admin_value=True)

    delete_calls = [call for call in st_stub.button.call_args_list if call.args and call.args[0] == "Delete User"]
    assert len(delete_calls) == 0
    st_stub.info.assert_called()


@pytest.mark.unit
def test_admin_username_exception_can_delete_other_admin() -> None:
    """The literal 'admin' account can delete other admin-group users."""
    session_state: dict = {"username": "admin", "_profile_user_id": "3", "user_id": 3}
    st_stub = _make_streamlit_stub(session_state)
    target_admin_user = {
        "id": 3,
        "name": "anotheradmin",
        "display_name": "Another Admin",
        "is_admin": True,
        "has_profile": True,
        "user_group_id": 1,
        "group_name": "admin",
    }
    _load_page_module(st_stub, session_state, user=target_admin_user, is_admin_value=True)

    delete_calls = [call for call in st_stub.button.call_args_list if call.args and call.args[0] == "Delete User"]
    assert len(delete_calls) == 1


@pytest.mark.unit
def test_non_superadmin_can_see_user_group_control_for_other_admin_user() -> None:
    """A non-'admin' account can change group for another admin user."""
    session_state: dict = {"username": "otheradmin", "_profile_user_id": "3", "user_id": 3}
    st_stub = _make_streamlit_stub(session_state)
    st_stub.form_submit_button = MagicMock(return_value=False)  # type: ignore[attr-defined]
    target_admin_user = {
        "id": 3,
        "name": "anotheradmin",
        "display_name": "Another Admin",
        "is_admin": True,
        "has_profile": True,
        "user_group_id": 1,
        "group_name": "admin",
    }
    _load_page_module(st_stub, session_state, user=target_admin_user, is_admin_value=True)

    user_group_submit_calls = [
        call for call in st_stub.form_submit_button.call_args_list if call.args and call.args[0] == "Update User Group"
    ]
    assert len(user_group_submit_calls) == 1


@pytest.mark.unit
def test_non_superadmin_cannot_change_own_user_group() -> None:
    """Non-superadmin cannot change their own user group."""
    session_state: dict = {"username": "otheradmin", "_profile_user_id": "3", "user_id": 3}
    st_stub = _make_streamlit_stub(session_state)
    target_self_user = {
        "id": 3,
        "name": "otheradmin",
        "display_name": "Other Admin",
        "is_admin": True,
        "has_profile": True,
        "user_group_id": 1,
        "group_name": "admin",
    }
    _load_page_module(st_stub, session_state, user=target_self_user, is_admin_value=True)

    user_group_submit_calls = [
        call for call in st_stub.form_submit_button.call_args_list if call.args and call.args[0] == "Update User Group"
    ]
    assert len(user_group_submit_calls) == 0


@pytest.mark.unit
def test_superadmin_cannot_change_own_user_group() -> None:
    """Superadmin cannot change their own user group."""
    session_state: dict = {"username": "admin", "_profile_user_id": "1", "user_id": 1}
    st_stub = _make_streamlit_stub(session_state)
    target_self_user = {
        "id": 1,
        "name": "admin",
        "display_name": "Admin",
        "is_admin": True,
        "has_profile": True,
        "user_group_id": 1,
        "group_name": "admin",
    }
    _load_page_module(st_stub, session_state, user=target_self_user, is_admin_value=True)

    user_group_submit_calls = [
        call for call in st_stub.form_submit_button.call_args_list if call.args and call.args[0] == "Update User Group"
    ]
    assert len(user_group_submit_calls) == 0


@pytest.mark.unit
def test_non_superadmin_cannot_change_superadmin_user_group() -> None:
    """Non-superadmin cannot change superadmin's user group."""
    session_state: dict = {"username": "otheradmin", "_profile_user_id": "1", "user_id": 3}
    st_stub = _make_streamlit_stub(session_state)
    superadmin_user = {
        "id": 1,
        "name": "admin",
        "display_name": "Admin",
        "is_admin": True,
        "has_profile": True,
        "user_group_id": 1,
        "group_name": "admin",
    }
    _load_page_module(st_stub, session_state, user=superadmin_user, is_admin_value=True)

    user_group_submit_calls = [
        call for call in st_stub.form_submit_button.call_args_list if call.args and call.args[0] == "Update User Group"
    ]
    assert len(user_group_submit_calls) == 0


@pytest.mark.unit
def test_non_superadmin_cannot_assign_admin_user_group() -> None:
    """Non-superadmin should not see admin in user-group choices."""
    session_state: dict = {"username": "otheradmin", "_profile_user_id": "2", "user_id": 2}
    st_stub = _make_streamlit_stub(session_state)
    regular_user = {
        "id": 2,
        "name": "targetuser",
        "display_name": "Target User",
        "is_admin": False,
        "has_profile": True,
        "user_group_id": 2,
        "group_name": "users",
    }
    _load_page_module(st_stub, session_state, user=regular_user, is_admin_value=True)

    user_group_select_calls = [
        call for call in st_stub.selectbox.call_args_list if call.args and call.args[0] == "User Group"
    ]
    assert len(user_group_select_calls) == 1
    assert "admin" not in user_group_select_calls[0].kwargs["options"]


@pytest.mark.unit
def test_profile_access_control_hidden_for_admin_group_users() -> None:
    """Admins should not see profile-access control for admin-group targets."""
    session_state: dict = {"username": "admin", "_profile_user_id": "3", "user_id": 3}
    st_stub = _make_streamlit_stub(session_state)
    st_stub.form_submit_button = MagicMock(return_value=False)  # type: ignore[attr-defined]
    target_admin_user = {
        "id": 3,
        "name": "anotheradmin",
        "display_name": "Another Admin",
        "is_admin": True,
        "has_profile": True,
        "user_group_id": 1,
        "group_name": "admin",
    }
    _load_page_module(st_stub, session_state, user=target_admin_user, is_admin_value=True)

    profile_access_submit_calls = [
        call
        for call in st_stub.form_submit_button.call_args_list
        if call.args and call.args[0] == "Update Profile Access"
    ]
    assert len(profile_access_submit_calls) == 0


@pytest.mark.unit
def test_profile_access_submit_updates_when_checkbox_changes() -> None:
    """Submitting changed profile access should call update function."""
    session_state: dict = {"username": "admin", "_profile_user_id": "2", "user_id": 2}
    st_stub = _make_streamlit_stub(session_state)
    st_stub.checkbox = MagicMock(return_value=False)  # type: ignore[attr-defined]

    def _submit_side_effect(label: str, **kwargs: object) -> bool:
        return label == "Update Profile Access"

    st_stub.form_submit_button = MagicMock(side_effect=_submit_side_effect)  # type: ignore[attr-defined]
    regular_user = {
        "id": 2,
        "name": "targetuser",
        "display_name": "Target User",
        "is_admin": False,
        "has_profile": True,
        "user_group_id": 2,
        "group_name": "users",
    }
    page = _load_page_module(st_stub, session_state, user=regular_user, is_admin_value=True)

    page._mock_update_has_profile.assert_called_once_with(2, False)
