"""User profile page - allows editing display name, password, and user group."""

from __future__ import annotations

import datetime as dt
import json
import os

import streamlit as st

from ui.components.sidebar import render_sidebar
from ui.constants import USER_PROFILE_PAGE_TITLE
from ui.db import session_repo
from ui.db.user_group_queries import list_user_groups
from ui.db.user_queries import (
    delete_user,
    get_user,
    update_user_has_profile,
    update_user_profile,
    update_user_user_group,
)
from ui.services.page_bootstrap import setup_page
from ui.services.permissions import can_edit_profile, is_admin
from ui.services.session import keys, lifecycle, session_manager

setup_page(page_title=USER_PROFILE_PAGE_TITLE, show_sidebar=False)

render_sidebar()

_FLASH_KEY = "profile_flash_message"


def _set_flash(level: str, message: str) -> None:
    st.session_state[_FLASH_KEY] = (level, message)


def _render_flash() -> None:
    flash = st.session_state.pop(_FLASH_KEY, None)
    if not flash:
        return
    level, message = flash
    if level == "success":
        st.success(message)
    elif level == "warning":
        st.warning(message)
    elif level == "info":
        st.info(message)
    else:
        st.error(message)


def _as_utc_datetime(value: object) -> dt.datetime | None:
    if isinstance(value, (int, float)):
        return dt.datetime.fromtimestamp(float(value), tz=dt.UTC)
    return lifecycle.ensure_utc(value)


def _seconds_left(value: object) -> int | None:
    ts = _as_utc_datetime(value)
    if ts is None:
        return None
    remaining = int((ts - dt.datetime.now(dt.UTC)).total_seconds())
    return max(0, remaining)


def _mask_token(value: object) -> str:
    if not value:
        return "<none>"
    token = str(value)
    return token if len(token) <= 10 else f"{token[:6]}...{token[-4:]}"


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _oidc_enabled() -> bool:
    raw = os.getenv("AUTH_MODES", "local")
    modes = [mode.strip().lower() for mode in str(raw).split(",") if mode.strip()]
    return any(mode != "local" for mode in modes)


def _render_session_debug_panel(*, is_self_edit: bool, is_admin_user: bool) -> None:
    if not is_self_edit or not _env_flag("UI_ENABLE_SESSION_DEBUG", False):
        return

    with st.expander("Session Debug"):
        st.caption("Debug-only session details for the currently logged-in user.")
        auth_source = st.session_state.get("auth_source", "unknown")
        oidc_enabled = _oidc_enabled() or str(auth_source or "").startswith("oidc:")
        if oidc_enabled:
            st.caption(
                "Note: `oidc.group_claim_path`, `oidc.group_claim_values`, and `oidc.group_mapping_match` "
                "are callback-time diagnostics. They are populated only during OIDC login callback and "
                "may be `null` after normal refresh/session restore."
            )
            col_refresh, col_token = st.columns(2)
            with col_refresh:
                st.button("Refresh Session Data", key="refresh_session_debug", width="stretch")
            with col_token:
                force_refresh_clicked = st.button("Refresh OIDC Token", key="refresh_oidc_token", width="stretch")
        else:
            st.button("Refresh Session Data", key="refresh_session_debug", width="stretch")
            force_refresh_clicked = False

        session_token = st.session_state.get(keys.SESSION_TOKEN)
        cookie_token = session_manager.get_session_token()
        db_session = session_repo.get_session_by_token(str(session_token)) if session_token else None

        if force_refresh_clicked:
            if str(auth_source or "").startswith("oidc:"):
                from ui.services.auth.oidc_refresh import _refresh_oidc_token

                refreshed = _refresh_oidc_token()
                if refreshed:
                    st.success("OIDC token refresh triggered successfully.")
                else:
                    st.error("OIDC token refresh failed.")
                st.rerun()
            else:
                st.info("OIDC token refresh is only available for OIDC sessions.")

        db_updated_at = lifecycle.ensure_utc(db_session.get("updated")) if db_session else None
        session_ttl_seconds = (
            max(0, int(lifecycle.session_ttl_remaining(db_updated_at).total_seconds())) if db_updated_at else None
        )

        debug_payload = {
            "auth_source": auth_source,
            "authenticated": bool(st.session_state.get(keys.AUTHENTICATED, False)),
            "session": {
                "session_token": _mask_token(session_token),
                "cookie_token": _mask_token(cookie_token),
                "db_session_found": db_session is not None,
                "db_updated_at_utc": db_updated_at.isoformat() if db_updated_at else None,
                "db_session_ttl_seconds": session_ttl_seconds,
            },
        }
        if oidc_enabled:
            oidc_access_expires_at = _as_utc_datetime(st.session_state.get("oidc_expires_at"))
            oidc_refresh_expires_at = _as_utc_datetime(st.session_state.get("oidc_refresh_expires_at"))
            oidc_id_token_exp = _as_utc_datetime(st.session_state.get("oidc_id_token_exp"))
            debug_payload["oidc"] = {
                "access_expires_at_utc": oidc_access_expires_at.isoformat() if oidc_access_expires_at else None,
                "access_ttl_seconds": _seconds_left(st.session_state.get("oidc_expires_at")),
                "refresh_expires_at_utc": oidc_refresh_expires_at.isoformat() if oidc_refresh_expires_at else None,
                "refresh_ttl_seconds": _seconds_left(st.session_state.get("oidc_refresh_expires_at")),
                "id_token_exp_utc": oidc_id_token_exp.isoformat() if oidc_id_token_exp else None,
                "id_token_ttl_seconds": _seconds_left(st.session_state.get("oidc_id_token_exp")),
                "has_access_token": bool(st.session_state.get("oidc_access_token")),
                "has_refresh_token": bool(st.session_state.get("oidc_refresh_token")),
                "has_id_token": bool(st.session_state.get("oidc_id_token")),
                "group_claim_path": st.session_state.get("oidc_group_claim_path"),
                "group_claim_values": st.session_state.get("oidc_group_claim_values"),
                "group_mapping_match": st.session_state.get("oidc_group_mapping_match"),
            }

        st.code(json.dumps(debug_payload, indent=2, sort_keys=False), language="json")


@st.dialog("Confirm Deletion")
def _confirm_delete_user_dialog(user_id: int, username: str) -> None:
    """Modal dialog to confirm deletion of a user account."""
    st.warning(f"Are you sure you want to delete user **{username}**?")
    st.caption("This action cannot be undone.")

    col_confirm, col_cancel = st.columns(2)

    with col_confirm:
        if st.button("Delete", type="primary", width="stretch"):
            success, message = delete_user(user_id)
            st.session_state["delete_user_result"] = (success, message)
            if success:
                st.switch_page("pages/Admin_Users.py")
            else:
                st.rerun()

    with col_cancel:
        if st.button("Cancel", width="stretch"):
            st.rerun()


# Resolve profile target from query params, then persisted state, then current session user.
query_user_id = st.query_params.get("user_id")
if query_user_id:
    st.session_state["_profile_user_id"] = str(query_user_id)
    user_id = query_user_id
else:
    user_id = st.session_state.get("_profile_user_id")

if not user_id:
    session_user_id = st.session_state.get(keys.USER_ID)
    if session_user_id is not None:
        user_id = str(session_user_id)
        st.session_state["_profile_user_id"] = user_id
    else:
        st.error("Session user ID not found.")
        st.stop()

try:
    user_id_int = int(user_id)
    user = get_user(user_id_int)
except (ValueError, TypeError):
    st.error("Invalid user ID.")
    st.stop()

if user is None:
    st.error("User not found.")
    st.stop()

# Display user info
st.info(f"Viewing profile for: **{user['name']}**")
_render_flash()

# Show result of a previous delete attempt (e.g. failure after rerun)
if "delete_user_result" in st.session_state:
    _success, _message = st.session_state.pop("delete_user_result")
    if _success:
        st.success(_message)
    else:
        st.error(_message)

# Guard: check if current user can edit this profile
if not can_edit_profile(user_id_int, target_username=user.get("name")):
    st.warning("You do not have permission to edit this profile.")
    st.stop()

session_has_profile = st.session_state.get(keys.HAS_PROFILE)
if not is_admin() and session_has_profile is not True:
    st.info("Your profile editing is disabled. Contact an administrator for assistance.")
    st.stop()

current_username = st.session_state.get(keys.USERNAME)
is_self_edit = current_username == user["name"]
st.title("Own User Profile" if is_admin() and is_self_edit else "User Profile")
_render_session_debug_panel(is_self_edit=is_self_edit, is_admin_user=is_admin())
is_superadmin = str(current_username or "").strip().lower() == "admin"
is_target_superadmin = str(user.get("name", "")).strip().lower() == "admin"
admin_group_modification_restricted = is_admin() and is_target_superadmin and not is_superadmin

if admin_group_modification_restricted:
    st.warning("Only the 'admin' account can modify the superadmin account.")

if not admin_group_modification_restricted:
    # Display name edit form
    with st.expander("Display Name"):
        with st.form("display_name_form"):
            current_display_name = user["display_name"] or ""
            new_display_name = st.text_input("Display Name", value=current_display_name, key="display_name_input")
            display_submitted = st.form_submit_button("Update Display Name", type="primary")

            if display_submitted:
                if not new_display_name.strip():
                    _set_flash("error", "Display name cannot be empty.")
                    st.rerun()
                elif new_display_name.strip() == current_display_name:
                    _set_flash("info", "No changes to display name.")
                    st.rerun()
                else:
                    success, message = update_user_profile(user_id_int, display_name=new_display_name.strip())
                    if success:
                        _set_flash("success", message)
                    else:
                        _set_flash("error", message)
                    st.rerun()

# User group edit section (admin-only controls)
if is_admin() and not admin_group_modification_restricted:
    if is_self_edit:
        with st.expander("User Group"):
            st.info("ℹ️ You cannot change your own user group.")
    else:
        with st.expander("User Group"):
            # Get all user groups for the dropdown
            user_groups = list_user_groups()
            if not is_superadmin:
                user_groups = [group for group in user_groups if str(group.get("name", "")).lower() != "admin"]

            if not user_groups:
                st.info("No user groups available for reassignment.")
            else:
                group_options = {g["name"]: g["id"] for g in user_groups}

                # Find the current group name
                current_group_name = user.get("group_name", "")
                current_group_id = user.get("user_group_id")

                with st.form("user_group_form"):
                    default_index = 0
                    group_names = list(group_options.keys())
                    if current_group_name in group_names:
                        default_index = group_names.index(current_group_name)

                    selected_group_name = st.selectbox(
                        "User Group",
                        options=group_names,
                        index=default_index,
                        key="user_group_select",
                    )
                    selected_group_id = group_options[selected_group_name]

                    group_submitted = st.form_submit_button("Update User Group", type="primary")

                    if group_submitted:
                        if selected_group_id == current_group_id:
                            _set_flash("info", "No changes to user group.")
                        else:
                            success, message = update_user_user_group(user_id_int, selected_group_id)
                            if success:
                                _set_flash("success", message)
                            else:
                                _set_flash("error", message)
                        st.rerun()

# Profile access edit form (admin-only, hidden for admin-group users)
if is_admin() and not admin_group_modification_restricted and str(user.get("group_name", "")).lower() != "admin":
    with st.expander("Profile Access"):
        current_has_profile = bool(user.get("has_profile"))
        profile_access_key = f"profile_access_checkbox_{user_id_int}"
        # Initialize once per target user; do not overwrite submitted form input on rerun.
        if profile_access_key not in st.session_state:
            st.session_state[profile_access_key] = current_has_profile
        with st.form("profile_access_form"):
            has_profile_value = st.checkbox(
                "Can edit profile",
                key=profile_access_key,
                help="If unchecked, user cannot change display name or password.",
            )
            profile_access_submitted = st.form_submit_button("Update Profile Access", type="primary")

            if profile_access_submitted:
                if has_profile_value == current_has_profile:
                    _set_flash("info", "No changes to profile access.")
                else:
                    success, message = update_user_has_profile(user_id_int, has_profile_value)
                    if success:
                        _set_flash("success", message)
                    else:
                        _set_flash("error", message)
                st.rerun()

# Password edit form
if not admin_group_modification_restricted:
    with st.expander("Change Password"):
        with st.form("password_form"):
            new_password = st.text_input("New Password", type="password", key="new_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
            password_submitted = st.form_submit_button("Update Password", type="primary")

            if password_submitted:
                if not new_password:
                    _set_flash("error", "Password cannot be empty.")
                    st.rerun()
                elif new_password != confirm_password:
                    _set_flash("error", "Passwords do not match.")
                    st.rerun()
                else:
                    success, message = update_user_profile(user_id_int, password=new_password)
                    if success:
                        _set_flash("success", message)
                    else:
                        _set_flash("error", message)
                    st.rerun()

# Delete User section (admin-only) — shown last
if is_admin() and not admin_group_modification_restricted:
    with st.expander("Delete User"):
        if current_username == user["name"]:
            st.info("You cannot delete your own account.")
        elif user["is_admin"] and current_username != "admin":
            st.info("Only the 'admin' account can delete other admin-group users.")
        else:
            if st.button("Delete User", type="primary", key="delete_user_btn"):
                _confirm_delete_user_dialog(user_id_int, user["name"])
