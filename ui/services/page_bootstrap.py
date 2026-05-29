"""Shared page bootstrap helpers for Streamlit pages."""

from __future__ import annotations

import streamlit as st
from streamlit.logger import get_logger

import ui.constants as constants
from ui.components.sidebar import render_sidebar
from ui.services.session import session_manager
from ui.services.session.state import (
    enforce_oidc_session_freshness,
    init_session_state,
    require_auth,
)

logger = get_logger(__name__)


def setup_page(
    *,
    page_title: str,
    layout: str | None = None,
    include_style: bool = True,
    require_login: bool = True,
    show_sidebar: bool = False,
) -> None:
    """Apply common page setup and optional auth/sidebar guards."""
    st.set_page_config(page_title=page_title, layout=layout or constants.APP_LAYOUT, page_icon=constants.APP_FAVICON)

    if include_style:
        st.markdown(constants.PAGE_STYLE, unsafe_allow_html=True)

    init_session_state()

    # Reuse a stable CookieManager across reruns to avoid auth redirect loops
    # caused by repeatedly re-instantiating the cookie component.
    session_manager.init()
    session_manager.restore_session()

    if require_login:
        enforce_oidc_session_freshness()
        require_auth()

    if show_sidebar:
        render_sidebar()
