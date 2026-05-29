"""Admin-only page for managing user groups and report membership."""

from __future__ import annotations

from collections import defaultdict

import streamlit as st

from ui.components.sidebar import render_sidebar
from ui.constants import USER_GROUPS_PAGE_TITLE
from ui.db.user_group_queries import (
    create_user_group,
    delete_user_group,
    exclude_report_from_group,
    get_report_ids_for_group,
    include_report_in_group,
    list_reports,
    list_user_groups,
    update_user_group_access_groups,
)
from ui.services.page_bootstrap import setup_page
from ui.services.permissions import is_admin, is_protected_group_name

setup_page(page_title=USER_GROUPS_PAGE_TITLE, show_sidebar=False)

# Admin-only access guard
if not is_admin():
    st.error("Access denied. This page is restricted to administrators.")
    st.stop()

render_sidebar()

st.title("User Groups")


@st.dialog("Confirm Deletion")
def _confirm_delete_dialog(group_id: int, group_name: str) -> None:
    """Modal dialog to confirm destructive deletion of a user group."""
    st.warning(f"Are you sure you want to delete the user group **{group_name}**?")
    st.caption("This action cannot be undone.")

    col_confirm, col_cancel = st.columns(2)

    with col_confirm:
        if st.button("Delete", type="primary", width="stretch"):
            result = delete_user_group(group_id)
            if result == "deleted":
                st.session_state["delete_group_result"] = (
                    "success",
                    f"User group '{group_name}' deleted successfully.",
                )
            elif result == "blocked_due_to_assignments":
                st.session_state["delete_group_result"] = (
                    "error",
                    f"Cannot delete '{group_name}': users are still assigned to this group.",
                )
            elif result == "not_found":
                st.session_state["delete_group_result"] = (
                    "warning",
                    f"User group '{group_name}' was not found.",
                )
            else:
                st.session_state["delete_group_result"] = (
                    "error",
                    f"An unexpected error occurred while deleting '{group_name}'.",
                )
            st.rerun()

    with col_cancel:
        if st.button("Cancel", width="stretch"):
            st.rerun()


# Handle delete result from previous rerun
if "delete_group_result" in st.session_state:
    level, message = st.session_state.pop("delete_group_result")
    if level == "success":
        st.success(message)
    elif level == "warning":
        st.warning(message)
    else:
        st.error(message)


# Handle form submission from previous rerun (create group)
if st.session_state.get("create_group_submitted"):
    data = st.session_state.pop("create_group_data")
    st.session_state.pop("create_group_submitted")

    success, message, _group_id = create_user_group(data["name"])
    if success:
        st.success(message)
    else:
        st.error(message)

# Handle update result from previous rerun (group report membership)
if "update_group_result" in st.session_state:
    level, message = st.session_state.pop("update_group_result")
    if level == "success":
        st.success(message)
    elif level == "warning":
        st.warning(message)
    else:
        st.error(message)

# Create user group form
with st.form("create_group_form"):
    name = st.text_input("Group Name", max_chars=100)

    submitted = st.form_submit_button("Create Group")

    if submitted:
        st.session_state["create_group_submitted"] = True
        st.session_state["create_group_data"] = {"name": name}
        st.rerun()


# List existing user groups
groups = list_user_groups()
reports = list_reports()

if not groups:
    st.info("No user groups available yet. Create one above to get started.")
else:
    # Group reports by report group_name for rendering
    reports_by_group: dict[str, list[dict]] = defaultdict(list)
    for report in reports:
        reports_by_group[report["group_name"]].append(report)

    for group in groups:
        group_id = group["id"]
        group_name = group["name"]

        # Get current report membership for this group
        included_report_ids = get_report_ids_for_group(group_id)

        with st.expander(group_name, expanded=False):
            if is_protected_group_name(group_name):
                st.info("All reports can be accessed.")
            elif not reports:
                st.info("No reports available to assign.")
            else:
                save_membership = False
                delete_requested = False
                with st.form(f"report_membership_form_{group_id}"):
                    selected_report_ids: set[int] = set()
                    access_group_filters = st.text_input(
                        "Access group filters",
                        value=group.get("access_groups") or "",
                        help="CSV list of access groups.",
                    )
                    st.write("")

                    # Render reports grouped by report group_name
                    for report_group_name, group_reports in reports_by_group.items():
                        st.markdown(f"**{report_group_name}**")

                        for report in group_reports:
                            report_id = report["id"]
                            report_name = report["report_name"]
                            is_included = report_id in included_report_ids

                            is_selected = st.checkbox(
                                report_name,
                                value=is_included,
                                key=f"toggle_{group_id}_{report_id}",
                            )
                            if is_selected:
                                selected_report_ids.add(report_id)

                        st.write("")  # Spacing between report groups

                    col_update, col_delete, _spacer = st.columns([1, 2, 6])
                    with col_update:
                        save_membership = st.form_submit_button(
                            "Update",
                            type="secondary",
                        )
                    with col_delete:
                        delete_requested = st.form_submit_button(
                            f"Delete '{group_name}' group",
                            type="primary",
                        )

                if save_membership:
                    update_user_group_access_groups(group_id, access_group_filters)

                    report_ids_to_include = selected_report_ids - included_report_ids
                    report_ids_to_exclude = included_report_ids - selected_report_ids

                    for report_id in report_ids_to_include:
                        include_report_in_group(group_id, report_id)

                    for report_id in report_ids_to_exclude:
                        exclude_report_from_group(group_id, report_id)

                    st.session_state["update_group_result"] = (
                        "success",
                        f"Updated report access for '{group_name}'.",
                    )
                    st.rerun()
                if delete_requested:
                    _confirm_delete_dialog(group_id, group_name)
