"""Concurrent network target sessions dashboard view."""

from __future__ import annotations

import streamlit as st

from ui.components.widgets.concurrent_network_targets import widget as concurrent_network_targets_widget
from ui.components.widgets.concurrent_users import data as concurrent_users_data
from ui.views.dashboard import (
    get_refresh_cooldown_state,
    mark_refresh,
    render_realtime_widget,
    render_refresh_warning,
    set_refresh_warning_state,
    should_bounce_refresh,
)


def render() -> None:
    """Render the concurrent network target sessions dashboard view."""
    cooldown_key = "dashboard_concurrent_network_targets_refresh_last_click"

    if st.button("Refresh", key="dashboard_concurrent_network_targets_refresh"):
        if should_bounce_refresh(cooldown_key):
            st.rerun()

        can_refresh, remaining_seconds = get_refresh_cooldown_state(cooldown_key, cooldown_seconds=10)
        if can_refresh:
            set_refresh_warning_state(cooldown_key, visible=False)
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
            key="dashboard_concurrent_network_targets_auto_refresh_enabled",
        )

    render_realtime_widget(
        lambda: concurrent_network_targets_widget.render(concurrent_users_data.fetch_data),
        auto_refresh_enabled=bool(auto_refresh_enabled),
        refresh_seconds=30,
    )
