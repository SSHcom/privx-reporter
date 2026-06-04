"""Overview dashboard view — entity counts at a glance."""

from __future__ import annotations

import streamlit as st

from ui.components.widgets.overview_counts import data as overview_data
from ui.components.widgets.overview_counts import widget as overview_widget
from ui.components.widgets.overview_directories import data as directories_data
from ui.components.widgets.overview_directories import widget as directories_widget
from ui.services.data_fetch_manager import get_data_fetch_manager
from ui.views.dashboard import (
    get_refresh_cooldown_state,
    mark_refresh,
    render_data_age_caption,
    render_refresh_warning,
    set_refresh_warning_state,
    should_bounce_refresh,
)


def render() -> None:
    """Render the overview dashboard view."""
    cooldown_key = "dashboard_overview_refresh_last_click"
    manager = get_data_fetch_manager()
    # Bump cache key when response schema changes (e.g. new trend fields)
    source_id = "overview_counts_v3"
    force_refresh = False

    if st.button("Refresh", key="dashboard_overview_refresh"):
        if not should_bounce_refresh(cooldown_key):
            can_refresh, remaining_seconds = get_refresh_cooldown_state(cooldown_key, cooldown_seconds=10)
            if can_refresh:
                set_refresh_warning_state(cooldown_key, visible=False)
                force_refresh = True
                mark_refresh(cooldown_key)
            else:
                set_refresh_warning_state(cooldown_key, visible=True)
        else:
            set_refresh_warning_state(cooldown_key, visible=False)

    render_refresh_warning(cooldown_key, cooldown_seconds=10)

    if not force_refresh and (not manager.has_cache(source_id) or not manager.has_cache("overview_directories")):
        st.info("No cached data yet. Click Refresh to load data.")
        render_data_age_caption(None)
        return

    source_readers = manager.load_page_data(
        "overview",
        {
            source_id: overview_data.fetch_data,
            "overview_directories": directories_data.fetch_data,
        },
        page_label="Overview",
        force_refresh=force_refresh,
        auto_refresh_stale=False,
        data_ttl_seconds=600,
    )
    data_age = manager.get_cache_age(source_id)
    render_data_age_caption(data_age)

    overview_widget.render(source_readers[source_id])

    st.divider()
    st.subheader("Directory sources")
    directories_widget.render(source_readers["overview_directories"])
