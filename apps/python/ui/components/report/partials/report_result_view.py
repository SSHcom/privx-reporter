"""Result rendering for report form submissions."""

from __future__ import annotations

import streamlit as st

from ui.components.datagrid import display_datagrid_with_pagination


def render_report_result(result: dict) -> None:
    """Render report output when display-to-page was requested."""
    if result["display_to_page"] and result["file_path"]:
        result_scope_key = str(result.get("scope_key", "default"))
        if result["json_data"] is not None:
            st.metric("Total records", len(result["json_data"]))
            st.json(result["json_data"])
        elif result["dataframe"] is not None:
            display_datagrid_with_pagination(result["dataframe"], scope_key=result_scope_key)
