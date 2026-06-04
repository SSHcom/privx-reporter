"""Admin-only page for managing alternative report group views."""

from __future__ import annotations

from collections import defaultdict

import streamlit as st

from ui.components.sidebar import render_sidebar
from ui.constants import REPORT_GROUPS_PAGE_TITLE
from ui.db.alt_group_queries import (
    add_reports_to_alt_group,
    create_alt_group_view,
    delete_alt_group_view,
    get_groups_for_view,
    list_alt_group_views,
    list_reports,
    remove_report_from_alt_group,
)
from ui.services.page_bootstrap import setup_page
from ui.services.permissions import is_admin
from ui.services.report_view_resolver import invalidate_report_view_cache

setup_page(page_title=REPORT_GROUPS_PAGE_TITLE, show_sidebar=False)

if not is_admin():
    st.error("Access denied. This page is restricted to administrators.")
    st.stop()

render_sidebar()

st.title("Report Groups")


@st.dialog("Confirm Deletion")
def _confirm_delete_dialog(view_id: int, view_name: str) -> None:
    st.warning(f"Are you sure you want to delete the report group view **{view_name}**?")
    st.caption("This also removes all report assignments for this view.")

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Delete", type="primary", width="stretch"):
            result = delete_alt_group_view(view_id)
            if result == "deleted":
                invalidate_report_view_cache()
                st.session_state["delete_view_result"] = (
                    "success",
                    f"Report group view '{view_name}' deleted successfully.",
                )
            elif result == "not_found":
                st.session_state["delete_view_result"] = (
                    "warning",
                    f"Report group view '{view_name}' was not found.",
                )
            else:
                st.session_state["delete_view_result"] = (
                    "error",
                    f"An unexpected error occurred while deleting '{view_name}'.",
                )
            st.rerun()
    with col_cancel:
        if st.button("Cancel", width="stretch"):
            st.rerun()


if "delete_view_result" in st.session_state:
    level, message = st.session_state.pop("delete_view_result")
    if level == "success":
        st.success(message)
    elif level == "warning":
        st.warning(message)
    else:
        st.error(message)

if st.session_state.get("create_report_group_view_submitted"):
    view_name = st.session_state.pop("create_report_group_view_name")
    st.session_state.pop("create_report_group_view_submitted")
    success, message, _view_id = create_alt_group_view(view_name)
    if success:
        invalidate_report_view_cache()
        st.success(message)
    else:
        st.error(message)

if st.session_state.get("add_report_assignment_submitted"):
    payload = st.session_state.pop("add_report_assignment_payload")
    st.session_state.pop("add_report_assignment_submitted")
    selected_report_ids = payload["report_ids"]
    if not selected_report_ids:
        st.warning("Select at least one report.")
    else:
        success, message = add_reports_to_alt_group(
            alt_group_view_id=payload["view_id"],
            group_name=payload["group_name"],
            report_ids=selected_report_ids,
        )
        if not success:
            st.error(message)
        else:
            invalidate_report_view_cache()
            st.success(f"Added {len(selected_report_ids)} report(s) to group '{payload['group_name'].strip()}'.")

with st.form("create_report_group_view_form"):
    view_name = st.text_input("View Name", max_chars=100)
    submitted = st.form_submit_button("Create Report Group View")
    if submitted:
        st.session_state["create_report_group_view_submitted"] = True
        st.session_state["create_report_group_view_name"] = view_name
        st.rerun()


views = list_alt_group_views()
reports = list_reports()

if not views:
    st.info("No report group views available yet. Create one above to get started.")
else:
    for view in views:
        view_id = view["id"]
        view_name = view["name"]
        assignments = get_groups_for_view(view_id)
        assignments_by_group: dict[str, list[dict]] = defaultdict(list)
        assigned_report_ids: set[int] = set()
        for row in assignments:
            assignments_by_group[row["group_name"]].append(row)
            assigned_report_ids.add(row["report_id"])

        with st.expander(view_name, expanded=False):
            available_report_options = {
                f"{report['group_name']} : {report['report_name']}": report["id"]
                for report in reports
                if report["id"] not in assigned_report_ids
            }

            if available_report_options:
                with st.form(f"add_assignment_form_{view_id}"):
                    group_name = st.text_input(
                        "New Group Name",
                        key=f"group_name_{view_id}",
                        placeholder="e.g. Operations",
                    )
                    selected_labels = st.multiselect(
                        "Reports",
                        options=list(available_report_options.keys()),
                        key=f"report_select_{view_id}",
                    )
                    add_assignment = st.form_submit_button("Create Group and Add Reports")
                    if add_assignment:
                        st.session_state["add_report_assignment_submitted"] = True
                        st.session_state["add_report_assignment_payload"] = {
                            "view_id": view_id,
                            "group_name": group_name,
                            "report_ids": [available_report_options[label] for label in selected_labels],
                        }
                        st.rerun()
            else:
                st.info("All reports in this view are already assigned to groups.")

            for group_name, rows in assignments_by_group.items():
                with st.expander(group_name, expanded=False):
                    for row in rows:
                        left, right = st.columns([7, 1])
                        with left:
                            st.write(f"{row['report_group_name']} : {row['report_name']}")
                        with right:
                            if st.button("Remove", key=f"remove_assignment_{row['id']}"):
                                remove_report_from_alt_group(row["id"])
                                invalidate_report_view_cache()
                                st.success("Assignment removed.")
                                st.rerun()

            if st.button(
                f"Delete '{view_name}' view",
                key=f"delete_view_{view_id}",
                type="primary",
            ):
                _confirm_delete_dialog(view_id, view_name)
