import streamlit as st

import ui.constants as constants
from lib.utils.string import to_ui_message
from ui.components.report import render_report, render_report_files
from ui.services.config_service import get_report_config
from ui.services.page_bootstrap import setup_page
from ui.services.report_service import can_access_report
from ui.services.session import keys
from ui.utils.string import normalize_name


def main() -> None:
    setup_page(page_title=constants.REPORTS_PAGE_TITLE, show_sidebar=True)

    selected_primary = st.session_state.get(keys.SELECTED_PRIMARY)
    selected_subcommand = st.session_state.get(keys.SELECTED_SUBCOMMAND)

    # Respect sidebar/session selection first; only use URL params as fallback.
    if (
        (not selected_primary or not selected_subcommand)
        and "primary" in st.query_params
        and "subcommand" in st.query_params
    ):
        selected_primary = st.query_params.primary
        selected_subcommand = st.query_params.subcommand
        st.session_state[keys.SELECTED_PRIMARY] = selected_primary
        st.session_state[keys.SELECTED_SUBCOMMAND] = selected_subcommand

    if selected_primary and selected_subcommand:
        # Check access using database-backed report visibility
        if not can_access_report(selected_primary, selected_subcommand):
            st.error("You do not have access to this report.")
            st.stop()

        st.title(f"{normalize_name(selected_primary)} :: {normalize_name(selected_subcommand)}")

        report_config = get_report_config()
        subcommand_config = report_config[selected_primary]["subcommands"][selected_subcommand]
        subcommand_key = f"{selected_primary}_{selected_subcommand}"

        st.write(f"**Help:** {to_ui_message(subcommand_config['help'])}")

        render_report(
            selected_primary,
            selected_subcommand,
            subcommand_config,
            subcommand_key,
        )
        render_report_files(
            selected_primary,
            selected_subcommand,
            subcommand_key,
        )
        return

    st.warning(constants.REPORTS_PAGE_DESCRIPTION)
    st.switch_page("pages/_1_Home.py")


main()
