"""Main report form renderer used by the Reports page."""

from __future__ import annotations

import streamlit as st

from ui.components.report.partials import render_dynamic_options, render_field_selector, render_report_result
from ui.services.privx_status import get_privx_connection_error
from ui.services.report_service import run_report
from ui.services.session import keys


def render_report(
    primary: str,
    subcommand: str,
    subcommand_config: dict,
    subcommand_key: str,
) -> None:
    """Render the report form with options, output mode toggles, and results."""
    result_key = keys.report_result_key(subcommand_key)

    selected_fields = None
    if "fields" in subcommand_config:
        with st.expander("Field Selection", expanded=False):
            selected_fields = render_field_selector(subcommand_config["fields"], subcommand_key)

    if "options" in subcommand_config:
        with st.form(key=f"form_{subcommand_key}"):
            form_values = render_dynamic_options(subcommand_config["options"], subcommand_key, primary, subcommand)

            json_output = st.checkbox("JSON", key=f"{subcommand_key}_json")

            display_to_page = False
            if subcommand_config["options"].get("ui_display", False):
                display_to_page = st.checkbox("Report to page", key=f"{subcommand_key}_display_to_page")

            ui_warning = subcommand_config["options"].get("ui_warning")
            if ui_warning:
                col1, col2 = st.columns([1, 6])
                with col1:
                    submitted = st.form_submit_button("Run Report")
                with col2:
                    st.info(ui_warning)
            else:
                submitted = st.form_submit_button("Run Report")

            if submitted:
                privx_error = get_privx_connection_error()
                if privx_error:
                    st.error(privx_error)
                    st.session_state[result_key] = {
                        "file_path": None,
                        "dataframe": None,
                        "json_data": None,
                        "json_output": json_output,
                        "display_to_page": display_to_page,
                        "error_message": privx_error,
                        "info_message": None,
                        "scope_key": subcommand_key,
                    }
                    return

                file_path, df, json_data, error_message, info_message = run_report(
                    primary, subcommand, form_values, display_to_page, json_output, selected_fields
                )
                if error_message:
                    st.error(error_message)
                if info_message:
                    st.info(info_message)
                st.session_state[result_key] = {
                    "file_path": file_path,
                    "dataframe": df,
                    "json_data": json_data,
                    "json_output": json_output,
                    "display_to_page": display_to_page,
                    "error_message": error_message,
                    "info_message": info_message,
                    "scope_key": subcommand_key,
                }
                if not error_message:
                    st.success(f"'{primary}/{subcommand}' report executed successfully")
                    # Expand files expander only when a report file was produced.
                    if not info_message:
                        st.session_state[keys.expand_files_key(subcommand_key)] = True
    else:
        with st.form(key=f"form_{subcommand_key}"):
            json_output = st.checkbox("JSON", key=f"{subcommand_key}_json")

            if st.form_submit_button("Run Report"):
                privx_error = get_privx_connection_error()
                if privx_error:
                    st.error(privx_error)
                    st.session_state[result_key] = {
                        "file_path": None,
                        "dataframe": None,
                        "json_data": None,
                        "json_output": json_output,
                        "display_to_page": False,
                        "error_message": privx_error,
                        "info_message": None,
                        "scope_key": subcommand_key,
                    }
                    return

                file_path, df, json_data, error_message, info_message = run_report(
                    primary, subcommand, None, False, json_output, selected_fields
                )
                if error_message:
                    st.error(error_message)
                if info_message:
                    st.info(info_message)
                st.session_state[result_key] = {
                    "file_path": file_path,
                    "dataframe": df,
                    "json_data": json_data,
                    "json_output": json_output,
                    "display_to_page": False,
                    "error_message": error_message,
                    "info_message": info_message,
                    "scope_key": subcommand_key,
                }
                if not error_message:
                    st.success(f"'{primary}/{subcommand}' report executed successfully")
                    # Expand files expander only when a report file was produced.
                    if not info_message:
                        st.session_state[keys.expand_files_key(subcommand_key)] = True

    if result_key in st.session_state:
        render_report_result(st.session_state[result_key])
