"""Tests for delete-related behavior in the Admin_User_Groups page.

These tests verify the dialog helper logic by importing the page module
with all Streamlit and DB dependencies fully mocked at the sys.modules level.
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
        "button",
    ):
        setattr(st, attr, MagicMock())
    st.columns = MagicMock(return_value=[MagicMock(), MagicMock()])  # type: ignore[attr-defined]
    return st


def _load_page_module(st_stub: types.ModuleType, session_state: dict) -> types.ModuleType:
    """Load Admin_User_Groups with all external dependencies mocked."""
    for key in list(sys.modules.keys()):
        if "Admin_User_Groups" in key:
            del sys.modules[key]

    mock_create = MagicMock(return_value=(False, "", None))
    mock_delete = MagicMock(return_value="deleted")
    mock_list_groups = MagicMock(return_value=[])
    mock_list_reports = MagicMock(return_value=[])
    mock_get_report_ids = MagicMock(return_value=set())
    mock_include = MagicMock()
    mock_exclude = MagicMock()
    mock_update_access_groups = MagicMock(return_value=True)
    mock_is_admin = MagicMock(return_value=True)
    mock_is_protected_group_name = MagicMock(return_value=False)
    mock_setup_page = MagicMock()
    mock_render_sidebar = MagicMock()

    ug_mod = types.ModuleType("ui.db.user_group_queries")
    ug_mod.create_user_group = mock_create  # type: ignore[attr-defined]
    ug_mod.delete_user_group = mock_delete  # type: ignore[attr-defined]
    ug_mod.list_user_groups = mock_list_groups  # type: ignore[attr-defined]
    ug_mod.list_reports = mock_list_reports  # type: ignore[attr-defined]
    ug_mod.get_report_ids_for_group = mock_get_report_ids  # type: ignore[attr-defined]
    ug_mod.include_report_in_group = mock_include  # type: ignore[attr-defined]
    ug_mod.exclude_report_from_group = mock_exclude  # type: ignore[attr-defined]
    ug_mod.update_user_group_access_groups = mock_update_access_groups  # type: ignore[attr-defined]

    perm_mod = types.ModuleType("ui.services.permissions")
    perm_mod.is_admin = mock_is_admin  # type: ignore[attr-defined]
    perm_mod.is_protected_group_name = mock_is_protected_group_name  # type: ignore[attr-defined]

    pb_mod = types.ModuleType("ui.services.page_bootstrap")
    pb_mod.setup_page = mock_setup_page  # type: ignore[attr-defined]

    sb_mod = types.ModuleType("ui.components.sidebar")
    sb_mod.render_sidebar = mock_render_sidebar  # type: ignore[attr-defined]

    const_mod = types.ModuleType("ui.constants")
    const_mod.USER_GROUPS_PAGE_TITLE = "User Groups"  # type: ignore[attr-defined]
    const_mod.PAGE_STYLE = ""  # type: ignore[attr-defined]

    overrides = {
        "streamlit": st_stub,
        "ui.db.user_group_queries": ug_mod,
        "ui.services.permissions": perm_mod,
        "ui.services.page_bootstrap": pb_mod,
        "ui.components.sidebar": sb_mod,
        "ui.constants": const_mod,
    }

    with patch.dict(sys.modules, overrides):
        import importlib

        import ui.pages.Admin_User_Groups as page_module

        importlib.reload(page_module)
        page_module._mock_delete_user_group = mock_delete  # type: ignore[attr-defined]
        return page_module


@pytest.mark.unit
def test_delete_dialog_confirm_deleted_sets_success_state() -> None:
    """Confirming deletion when result is 'deleted' stores a success tuple."""
    session_state: dict = {}
    st_stub = _make_streamlit_stub(session_state)
    page = _load_page_module(st_stub, session_state)

    page._mock_delete_user_group.return_value = "deleted"

    call_count = [0]

    def mock_button(label: str, **kwargs: object) -> bool:
        call_count[0] += 1
        return call_count[0] == 1

    st_stub.button.side_effect = mock_button

    page._confirm_delete_dialog(group_id=1, group_name="TestGroup")

    page._mock_delete_user_group.assert_called_once_with(1)
    assert session_state.get("delete_group_result") == (
        "success",
        "User group 'TestGroup' deleted successfully.",
    )


@pytest.mark.unit
def test_delete_dialog_confirm_blocked_sets_error_state() -> None:
    """Confirming deletion when blocked stores an error tuple with assignment hint."""
    session_state: dict = {}
    st_stub = _make_streamlit_stub(session_state)
    page = _load_page_module(st_stub, session_state)

    page._mock_delete_user_group.return_value = "blocked_due_to_assignments"

    call_count = [0]

    def mock_button(label: str, **kwargs: object) -> bool:
        call_count[0] += 1
        return call_count[0] == 1

    st_stub.button.side_effect = mock_button

    page._confirm_delete_dialog(group_id=2, group_name="BlockedGroup")

    page._mock_delete_user_group.assert_called_once_with(2)
    level, message = session_state["delete_group_result"]
    assert level == "error"
    assert "BlockedGroup" in message
    assert "assigned" in message


@pytest.mark.unit
def test_delete_dialog_cancel_does_not_call_delete() -> None:
    """Pressing Cancel does not invoke delete_user_group and leaves state untouched."""
    session_state: dict = {}
    st_stub = _make_streamlit_stub(session_state)
    page = _load_page_module(st_stub, session_state)

    call_count = [0]

    def mock_button(label: str, **kwargs: object) -> bool:
        call_count[0] += 1
        return call_count[0] == 2

    st_stub.button.side_effect = mock_button

    page._confirm_delete_dialog(group_id=3, group_name="SomeGroup")

    page._mock_delete_user_group.assert_not_called()
    assert "delete_group_result" not in session_state
