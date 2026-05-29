from __future__ import annotations

import streamlit as st
from streamlit.logger import get_logger

from ui.services.page_bootstrap import setup_page
from ui.services.permissions import is_admin
from ui.services.privx_status import get_privx_connection_error
from ui.services.session import keys
from ui.views.dashboard import (
    overview,
    performance_activity,
    system_health_compliance,
)

logger = get_logger(__name__)

_VIEWS = {
    "overview": {
        "label": "Overview",
        "renderer": overview.render,
    },
    "performance_activity": {
        "label": "Performance & Activity",
        "renderer": performance_activity.render,
    },
    "system_health_compliance": {
        "label": "Certificate Status",
        "renderer": system_health_compliance.render,
    },
}

_DEFAULT_VIEW = "overview"
_PERSISTED_VIEW_KEY = "dashboard_view_persisted"
_LAST_ACTIVE_VIEW_KEY = "dashboard_last_active_view"
_VIEW_CHANGE_SERIAL_KEY = "dashboard_view_change_serial"


def main() -> None:
    setup_page(page_title="Dashboard", show_sidebar=True)

    if not is_admin():
        st.error("Access denied. This page is restricted to administrators.")
        st.stop()

    privx_error = get_privx_connection_error()
    if privx_error:
        st.warning(privx_error)
        st.info("Dashboard data loading is paused until PrivX connection is restored.")
        st.stop()

    logger.info(
        "dashboard.main start has_dashboard_view=%s dashboard_view=%s has_persisted=%s persisted_view=%s",
        keys.DASHBOARD_VIEW in st.session_state,
        st.session_state.get(keys.DASHBOARD_VIEW),
        _PERSISTED_VIEW_KEY in st.session_state,
        st.session_state.get(_PERSISTED_VIEW_KEY),
    )

    options = list(_VIEWS.keys())
    persisted_view = st.session_state.get(_PERSISTED_VIEW_KEY, _DEFAULT_VIEW)

    if persisted_view not in _VIEWS:
        logger.warning(
            "dashboard.main invalid persisted view=%s fallback=%s",
            persisted_view,
            _DEFAULT_VIEW,
        )
        persisted_view = _DEFAULT_VIEW

    if keys.DASHBOARD_VIEW not in st.session_state:
        st.session_state[keys.DASHBOARD_VIEW] = persisted_view
        logger.info("dashboard.main initialized dashboard_view from persisted=%s", persisted_view)
    elif st.session_state[keys.DASHBOARD_VIEW] not in _VIEWS:
        logger.warning(
            "dashboard.main invalid dashboard_view=%s fallback_to_persisted=%s",
            st.session_state[keys.DASHBOARD_VIEW],
            persisted_view,
        )

        st.session_state[keys.DASHBOARD_VIEW] = persisted_view
    selector_col, _ = st.columns([1, 1])

    with selector_col:
        st.selectbox(
            "View dashboard",
            options=options,
            format_func=lambda value: _VIEWS[value]["label"],
            key=keys.DASHBOARD_VIEW,
            width="stretch",
        )

    active_view = st.session_state[keys.DASHBOARD_VIEW]
    st.session_state[_PERSISTED_VIEW_KEY] = active_view
    last_active_view = st.session_state.get(_LAST_ACTIVE_VIEW_KEY)
    if last_active_view != active_view:
        st.session_state[_VIEW_CHANGE_SERIAL_KEY] = int(st.session_state.get(_VIEW_CHANGE_SERIAL_KEY, 0)) + 1
        st.session_state[_LAST_ACTIVE_VIEW_KEY] = active_view

    logger.info(
        "dashboard.main selected active_view=%s persisted_view=%s",
        active_view,
        st.session_state.get(_PERSISTED_VIEW_KEY),
    )

    st.title(f"Dashboard :: {_VIEWS[active_view]['label']}")
    _VIEWS[active_view]["renderer"]()


main()
