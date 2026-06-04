from __future__ import annotations

import streamlit as st

from ui.components.home_logo_link import render_home_logo_link
from ui.services.auth.oidc_logout import logout_user
from ui.services.permissions import is_admin
from ui.services.report_view_resolver import ResolvedView, get_resolved_report_views
from ui.services.session import keys, session_manager
from ui.utils.string import normalize_name


def _render_report_tree(view: ResolvedView) -> None:
    """Render one resolved view worth of report groups."""
    is_default_view = view["id"] is None
    for group in view["groups"]:
        should_expand = is_default_view and st.session_state.get(keys.SELECTED_PRIMARY) == group["name"]
        group_label = normalize_name(group["name"]) if is_default_view else group["name"]
        with st.expander(group_label, expanded=should_expand):
            for report in group["reports"]:
                if is_default_view:
                    button_label = normalize_name(report["subcommand"])
                else:
                    button_label = f"{normalize_name(report['primary'])} : {normalize_name(report['subcommand'])}"
                button_key = f"view_{view['id']}_{group['name']}_{report['primary']}_{report['subcommand']}"
                if st.button(button_label, key=button_key, width="stretch"):
                    st.session_state[keys.SELECTED_PRIMARY] = report["primary"]
                    st.session_state[keys.SELECTED_SUBCOMMAND] = report["subcommand"]
                    st.switch_page("pages/_2_Reports.py")


def render_sidebar() -> None:
    """Render the report navigation sidebar."""

    with st.sidebar:
        if render_home_logo_link():
            st.session_state[keys.SELECTED_PRIMARY] = None
            st.session_state[keys.SELECTED_SUBCOMMAND] = None
            st.switch_page("pages/_1_Home.py")

        display_name = st.session_state.get(keys.DISPLAY_NAME) or st.session_state.get(keys.USERNAME, "")

        auth_source = st.session_state.get("auth_source")
        if str(auth_source or "").startswith("oidc"):
            # logout_label = "Log out of IdP"
            if display_name:
                st.markdown(
                    f"<span style='color: rgba(250,250,250,0.75);'>Logged in as </span>"
                    f"<span style='color: white; font-weight: 700;'>{display_name}</span>"
                    f"<span style='color: rgba(250,250,250,0.75);'> with IdP ({auth_source})</span>",
                    unsafe_allow_html=True,
                )
        else:
            if display_name:
                st.caption(f"Logged in as **{display_name}**")

        st.title("Reports")

        if st.button("Report Files", key="report_files_button", width="stretch"):
            st.switch_page("pages/_3_Report_Files.py")

        resolved_views = get_resolved_report_views()
        if not resolved_views:
            st.info("No reports available for your account.")
        else:
            selected_name = st.session_state.get(keys.SELECTED_ALT_GROUP_VIEW, "Default")
            selected_names = [view["name"] for view in resolved_views]
            if selected_name not in selected_names:
                selected_name = selected_names[0]

            selected_name = st.selectbox(
                "Report View",
                options=selected_names,
                index=selected_names.index(selected_name),
                key="report_group_view_picker",
            )
            st.session_state[keys.SELECTED_ALT_GROUP_VIEW] = selected_name

            selected_view = next(view for view in resolved_views if view["name"] == selected_name)
            _render_report_tree(selected_view)

        # Administration section (admin-only)
        if is_admin():
            st.title("Administration")
            if st.button("Dashboard", key="dashboard_button", width="stretch"):
                st.switch_page("pages/Admin_Dashboard.py")
            if st.button("Sync Status", key="sync_status_button", width="stretch"):
                st.switch_page("pages/Admin_Sync_Status.py")
            if st.button("Users", key="users_button", width="stretch"):
                st.switch_page("pages/Admin_Users.py")
            if st.button("User Groups", key="user_groups_button", width="stretch"):
                st.switch_page("pages/Admin_User_Groups.py")
            if st.button("Report Groups", key="report_groups_button", width="stretch"):
                st.switch_page("pages/Admin_Report_Group.py")

        # Account section
        st.title("Account")

        # display_name = st.session_state.get(keys.DISPLAY_NAME) or st.session_state.get(keys.USERNAME, "")
        # if display_name:
        #    st.caption(f"Logged in as **{display_name}**")

        auth_source = st.session_state.get("auth_source")
        if str(auth_source or "").startswith("oidc"):
            logout_label = "Log out of IdP"
        else:
            logout_label = "Logout"

        has_profile = st.session_state.get(keys.HAS_PROFILE)
        if is_admin() or has_profile is True:
            if st.button("My Profile", key="profile_button", width="stretch"):
                user_id = st.session_state.get(keys.USER_ID)
                if user_id is not None:
                    st.session_state["_profile_user_id"] = str(user_id)
                st.switch_page("pages/Admin_User_Profile.py")

        if st.button(logout_label, key="logout_button", width="stretch"):
            if str(auth_source or "").startswith("oidc"):
                logout_user()
            else:
                session_manager.end_session(redirect=True)
