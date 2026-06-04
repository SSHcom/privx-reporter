"""Behavior and risk analytics dashboard view."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import streamlit as st
from streamlit.logger import get_logger

from ui.components.widgets import behavior_risk_group
from ui.services.data_fetch_manager import get_data_fetch_manager
from ui.views.dashboard import (
    get_refresh_cooldown_state,
    mark_refresh,
    render_data_age_caption,
    render_refresh_warning,
    render_widget_rows,
    set_refresh_warning_state,
    should_bounce_refresh,
)

logger = get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable


def _with_render_timing(name: str, renderer: Callable[[], None]) -> Callable[[], None]:
    """Wrap widget rendering with timing logs."""

    def _wrapped() -> None:
        started_at = time.perf_counter()
        renderer()
        logger.debug(
            "behavior_risk.widget[%s] render took %.2fs",
            name,
            time.perf_counter() - started_at,
        )

    return _wrapped


def _handle_refresh(cooldown_key: str, refresh_requested: bool) -> bool:
    """Handle refresh request and return whether force-refresh is requested."""
    force_refresh = False

    if refresh_requested:
        if should_bounce_refresh(cooldown_key):
            logger.info("behavior_risk.refresh bounced reason=fetch_in_progress")
            return False

        can_refresh, remaining_seconds = get_refresh_cooldown_state(cooldown_key, cooldown_seconds=10)
        if can_refresh:
            set_refresh_warning_state(cooldown_key, visible=False)
            force_refresh = True
            mark_refresh(cooldown_key)
            logger.info("behavior_risk.refresh accepted cooldown_seconds=%s", 10)
        else:
            set_refresh_warning_state(cooldown_key, visible=True)
            logger.info("behavior_risk.refresh blocked remaining_seconds=%s", remaining_seconds)

    return force_refresh


def _load_sources(days: int, top_n: int, force_refresh: bool) -> Callable[[], dict[str, object]] | None:
    """Load behavior risk source through DataFetchManager and return cached reader."""
    manager = get_data_fetch_manager()
    source_id = f"behavior_risk_d{days}_n{top_n}"

    if not force_refresh and not manager.has_cache(source_id):
        st.info("No cached data yet for this selection. Click Refresh to load data.")
        render_data_age_caption(None)
        return None

    progress_caption = st.empty()
    request_started_at = time.perf_counter()

    logger.debug(
        "behavior_risk.request start source_id=%s days=%s top_n=%s force_refresh=%s",
        source_id,
        days,
        top_n,
        force_refresh,
    )

    def _fetch_source() -> dict[str, object]:
        return behavior_risk_group.data.fetch_data(days, top_n)

    sources = manager.load_page_data(
        "behavior_risk",
        {source_id: _fetch_source},
        page_label="Behavior & Risk Analytics",
        force_refresh=force_refresh,
        auto_refresh_stale=False,
        on_progress=lambda done, total: progress_caption.caption(f"Refreshed {done} of {total}"),
        data_ttl_seconds=600,  # 10 minutes
    )

    progress_caption.empty()
    data_age = manager.get_cache_age(source_id)
    logger.debug(
        "behavior_risk.request done source_id=%s force_refresh=%s data_age=%s elapsed=%.2fs",
        source_id,
        force_refresh,
        "none" if data_age is None else int(data_age),
        time.perf_counter() - request_started_at,
    )

    render_data_age_caption(data_age)

    return sources[source_id]


def render() -> None:
    """Render behavior and risk analytics dashboard view."""
    cooldown_key = "dashboard_behavior_risk_refresh_last_click"
    st.caption("Analytics window uses recent connection records from data DB. (limited to 100k rows)")

    with st.form("behavior_risk_params"):
        selected_days = st.selectbox(
            "Analytics window",
            options=[7, 14, 30],
            index=0,
            format_func=lambda value: f"Last {value} days",
            key="dashboard_behavior_risk_days",
        )
        selected_top_n = st.selectbox(
            "Top N",
            options=[5, 10, 20, 50],
            index=1,
            key="dashboard_behavior_risk_top_n",
        )
        refresh_requested = st.form_submit_button("Refresh")

    force_refresh = _handle_refresh(cooldown_key, refresh_requested)
    render_refresh_warning(cooldown_key, cooldown_seconds=10)
    source_reader = _load_sources(int(selected_days), int(selected_top_n), force_refresh)
    if source_reader is None:
        return

    render_widget_rows(
        [
            _with_render_timing(
                "ueba_usual",
                lambda: behavior_risk_group.widget_ueba_usual_connections.render(source_reader),
            ),
            _with_render_timing(
                "ueba_anomaly",
                lambda: behavior_risk_group.widget_ueba_anomaly_connections.render(source_reader),
            ),
            _with_render_timing(
                "top_privx_users",
                lambda: behavior_risk_group.widget_top_privx_users.render(
                    source_reader,
                    top_n=int(selected_top_n),
                ),
            ),
            _with_render_timing(
                "top_api_users",
                lambda: behavior_risk_group.widget_top_api_users.render(
                    source_reader,
                    top_n=int(selected_top_n),
                ),
            ),
            _with_render_timing(
                "top_target_accounts",
                lambda: behavior_risk_group.widget_top_target_accounts.render(
                    source_reader,
                    top_n=int(selected_top_n),
                ),
            ),
        ],
        max_per_row=2,
    )
