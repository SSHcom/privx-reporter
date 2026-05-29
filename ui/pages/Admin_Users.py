"""Admin-only page for listing and creating users."""

from __future__ import annotations

import streamlit as st
from streamlit_extras.specialized_inputs import password_input

from ui.components.sidebar import render_sidebar
from ui.constants import USERS_PAGE_TITLE
from ui.db.user_group_queries import list_user_groups
from ui.db.user_queries import create_user, list_users
from ui.services.page_bootstrap import setup_page
from ui.services.permissions import is_admin
from ui.services.session import keys

setup_page(page_title=USERS_PAGE_TITLE, show_sidebar=False)

# Admin-only access guard
if not is_admin():
    st.error("Access denied. This page is restricted to administrators.")
    st.stop()

render_sidebar()

st.title("Users")

# Handle form submission from previous rerun
if st.session_state.get("create_user_submitted"):
    data = st.session_state.pop("create_user_data")
    st.session_state.pop("create_user_submitted")

    # Validate required fields
    errors = []
    if not data["name"].strip():
        errors.append("Username is required")
    if not data["display_name"].strip():
        errors.append("Display Name is required")
    if not data["password"]:
        errors.append("Password is required")

    if errors:
        for error in errors:
            st.error(error)
    else:
        success, message = create_user(
            name=data["name"].strip(),
            display_name=data["display_name"].strip(),
            user_group_id=data["group_id"],
            password=data["password"],
            has_profile=data["has_profile"],
        )
        if success:
            st.success(message)
        else:
            st.error(message)

# Create user form (inside expander)
groups = list_user_groups()
current_username = st.session_state.get(keys.USERNAME)
can_assign_admin_group = current_username == "admin"

if not can_assign_admin_group:
    groups = [group for group in groups if str(group.get("name", "")).lower() != "admin"]

if not groups:
    st.error("No user groups available for your account. Contact the superadmin.")
else:
    with st.expander("Create User", expanded=False):
        group_options = {g["name"]: g["id"] for g in groups}
        st.session_state.setdefault("create_user_has_profile", True)
        selected_group = st.selectbox(
            "User Group",
            options=list(group_options.keys()),
            key="create_user_group_select",
        )
        is_admin_group_selected = selected_group.strip().lower() == "admin"

        with st.form("create_user_form"):
            name = st.text_input("Username", max_chars=50)
            display_name = st.text_input("Display Name", max_chars=100)

            password = password_input("Password")
            if is_admin_group_selected:
                st.session_state["create_user_has_profile"] = True
            has_profile = st.checkbox(
                "Can edit profile",
                key="create_user_has_profile",
                disabled=is_admin_group_selected,
                help="If unchecked, user cannot change display name or password",
            )

            submitted = st.form_submit_button("Create User")

            if submitted:
                st.session_state["create_user_submitted"] = True
                st.session_state["create_user_data"] = {
                    "name": name,
                    "display_name": display_name,
                    "group_id": group_options[selected_group],
                    "password": password,
                    "has_profile": True if is_admin_group_selected else has_profile,
                }
                st.rerun()

# User list table
st.subheader("User List")

users = list_users()

if not users:
    st.info("No users found.")
else:
    # Column headers
    col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 1, 1, 1])
    col1.write("**Name**")
    col2.write("**Display Name**")
    col3.write("**Group**")
    col4.write("**Super admin**")
    col5.write("**Profile**")
    col6.write("**Actions**")

    st.divider()

    for user in users:
        col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 1, 1, 1])
        col1.write(user["name"])
        col2.write(user["display_name"])
        col3.write(user["group_name"])
        col4.write("✓" if user["is_admin"] else "")
        col5.checkbox(
            "Can edit",
            value=user["has_profile"],
            key=f"has_profile_{user['id']}",
            disabled=True,
            label_visibility="collapsed",
        )
        with col6:
            if st.button("Edit", key=f"profile_{user['id']}"):
                st.session_state["_profile_user_id"] = str(user["id"])
                st.switch_page("pages/Admin_User_Profile.py")
