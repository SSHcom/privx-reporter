import streamlit as st

import ui.constants as constants
from ui.services.page_bootstrap import setup_page
from ui.services.session import keys


def main() -> None:
    setup_page(page_title=constants.HOME_PAGE_TITLE, show_sidebar=True)

    if st.session_state.get(keys.SELECTED_PRIMARY) and st.session_state.get(keys.SELECTED_SUBCOMMAND):
        st.switch_page("pages/_2_Reports.py")
    else:
        st.info(constants.HOME_PAGE_DESCRIPTION)


main()
