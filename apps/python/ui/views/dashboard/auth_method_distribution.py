"""PrivX user authentication method distribution dashboard view."""

from __future__ import annotations

import streamlit as st

from ui.components.widgets.auth_method_distribution import data as auth_method_distribution_data
from ui.components.widgets.auth_method_distribution import widget as auth_method_distribution_widget
from ui.views.dashboard import (
    get_refresh_cooldown_state,
    mark_refresh,
    render_realtime_widget,
    render_refresh_warning,
    set_refresh_warning_state,
    should_bounce_refresh,
)


def render() -> None:
    """Render authentication method distribution dashboard view."""
    cooldown_key = "dashboard_auth_method_distribution_refresh_last_click"

    if st.button("Refresh", key="dashboard_auth_method_distribution_refresh"):
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
            key="dashboard_auth_method_distribution_auto_refresh_enabled",
        )

    render_realtime_widget(
        lambda: auth_method_distribution_widget.render(auth_method_distribution_data.fetch_data),
        auto_refresh_enabled=bool(auto_refresh_enabled),
        refresh_seconds=30,
    )
