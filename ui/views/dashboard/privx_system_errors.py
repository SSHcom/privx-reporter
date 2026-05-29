"""Collected PrivX system errors dashboard view."""

from __future__ import annotations

import streamlit as st

from ui.components.widgets.system_health_compliance_group import data as system_health_compliance_data
from ui.components.widgets.system_health_compliance_group import (
    widget_privx_system_errors as system_health_compliance_widget_privx_system_errors,
)
from ui.views.dashboard import (
    get_refresh_cooldown_state,
    mark_refresh,
    render_realtime_widget,
    render_refresh_warning,
    set_refresh_warning_state,
    should_bounce_refresh,
)


def render() -> None:
    """Render collected PrivX system errors dashboard view."""
    cooldown_key = "dashboard_privx_system_errors_refresh_last_click"

    if st.button("Refresh", key="dashboard_privx_system_errors_refresh"):
        if should_bounce_refresh(cooldown_key):
            st.rerun()

        can_refresh, remaining_seconds = get_refresh_cooldown_state(cooldown_key, cooldown_seconds=10)
        if can_refresh:
            set_refresh_warning_state(cooldown_key, visible=False)
            system_health_compliance_data.fetch_privx_system_errors_data.clear()
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
            key="dashboard_privx_system_errors_auto_refresh_enabled",
        )

    render_realtime_widget(
        lambda: system_health_compliance_widget_privx_system_errors.render(
            system_health_compliance_data.fetch_privx_system_errors_data
        ),
        auto_refresh_enabled=bool(auto_refresh_enabled),
        refresh_seconds=30,
    )
