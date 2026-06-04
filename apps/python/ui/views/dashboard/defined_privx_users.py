"""Defined PrivX users dashboard view."""

from __future__ import annotations

import streamlit as st

from ui.components.widgets.defined_privx_users import data as defined_privx_users_data
from ui.components.widgets.defined_privx_users import widget as defined_privx_users_widget
from ui.views.dashboard import (
    get_refresh_cooldown_state,
    mark_refresh,
    render_realtime_widget,
    render_refresh_warning,
    set_refresh_warning_state,
    should_bounce_refresh,
)


def render() -> None:
    """Render total defined PrivX users dashboard view."""
    cooldown_key = "dashboard_defined_privx_users_refresh_last_click"

    if st.button("Refresh", key="dashboard_defined_privx_users_refresh"):
        if should_bounce_refresh(cooldown_key):
            st.rerun()

        can_refresh, remaining_seconds = get_refresh_cooldown_state(cooldown_key, cooldown_seconds=10)
        if can_refresh:
            set_refresh_warning_state(cooldown_key, visible=False)
            defined_privx_users_data.fetch_data.clear()
            mark_refresh(cooldown_key)
            st.rerun()
        else:
            set_refresh_warning_state(cooldown_key, visible=True)

    render_refresh_warning(cooldown_key, cooldown_seconds=10)

    refresh_col, _ = st.columns([1, 5])
    with refresh_col:
        auto_refresh_enabled = st.checkbox(
            "Auto-refresh every 30s",
            value=False,
            key="dashboard_defined_privx_users_auto_refresh_enabled",
        )

    render_realtime_widget(
        lambda: defined_privx_users_widget.render(defined_privx_users_data.fetch_data),
        auto_refresh_enabled=bool(auto_refresh_enabled),
        refresh_seconds=30,
    )
