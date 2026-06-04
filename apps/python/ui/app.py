import streamlit as st

import ui.constants as constants
from ui.bootstrap import configure_logging
from ui.services.config_service import get_report_config
from ui.services.session import keys
from ui.services.session.state import init_session_state

# Reuse bootstrap setup so app/runtime initialization stays centralized.
configure_logging(force=True)

st.set_page_config(page_title=constants.APP_TITLE, layout=constants.APP_LAYOUT, page_icon=constants.APP_FAVICON)

init_session_state()

report_config = get_report_config()

if st.session_state.get(keys.AUTHENTICATED, False):
    st.switch_page("pages/_1_Home.py")
else:
    st.switch_page("pages/_0_Login.py")
