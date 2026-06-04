"""Counters dashboard view."""

from __future__ import annotations

import streamlit as st

from ui.components.widgets import (
    auth_method_distribution,
    concurrent_client_methods,
    concurrent_file_transfer,
    concurrent_network_targets,
    concurrent_protocols,
    concurrent_users,
)
from ui.views.dashboard import (
    get_refresh_cooldown_state,
    mark_refresh,
    render_refresh_warning,
    render_widget_rows,
    set_refresh_warning_state,
    should_bounce_refresh,
)


def render() -> None:
    """Render the Counters dashboard view."""
    cooldown_key = "dashboard_counters_refresh_last_click"

    if st.button("Refresh", key="dashboard_counters_refresh"):
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

    render_widget_rows(
        [
            lambda: concurrent_users.widget.render(concurrent_users.data.fetch_data),
            lambda: concurrent_protocols.widget.render(concurrent_users.data.fetch_data),
            lambda: concurrent_network_targets.widget.render(concurrent_users.data.fetch_data),
            lambda: concurrent_file_transfer.widget.render(concurrent_users.data.fetch_data),
            lambda: concurrent_client_methods.widget.render(concurrent_users.data.fetch_data),
            lambda: auth_method_distribution.widget.render(auth_method_distribution.data.fetch_data),
        ],
        max_per_row=2,
    )
