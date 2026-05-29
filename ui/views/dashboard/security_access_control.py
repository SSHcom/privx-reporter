"""Security and access control dashboard view."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import streamlit as st
from streamlit.logger import get_logger

from ui.components.widgets import security_access_group
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
        logger.info(
            "security_access.widget[%s] render took %.2fs",
            name,
            time.perf_counter() - started_at,
        )

    return _wrapped


def _handle_refresh(cooldown_key: str, refresh_requested: bool) -> bool:
    """Handle refresh request and return whether force-refresh is requested."""
    force_refresh = False

    if refresh_requested:
        if should_bounce_refresh(cooldown_key):
            logger.info("security_access.refresh bounced reason=fetch_in_progress")
            return False

        can_refresh, remaining_seconds = get_refresh_cooldown_state(cooldown_key, cooldown_seconds=10)
        if can_refresh:
            set_refresh_warning_state(cooldown_key, visible=False)
            force_refresh = True
            mark_refresh(cooldown_key)
            logger.info("security_access.refresh accepted cooldown_seconds=%s", 10)
        else:
            set_refresh_warning_state(cooldown_key, visible=True)
            logger.info("security_access.refresh blocked remaining_seconds=%s", remaining_seconds)

    return force_refresh


def _load_sources(days: int, force_refresh: bool) -> Callable[[], dict[str, object]] | None:
    """Load security and access source through DataFetchManager and return cached reader."""
    manager = get_data_fetch_manager()
    source_id = f"security_access_d{days}"

    if not force_refresh and not manager.has_cache(source_id):
        st.info("No cached data yet for this selection. Click Refresh to load data.")
        render_data_age_caption(None)
        return None

    progress_caption = st.empty()
    request_started_at = time.perf_counter()

    logger.info(
        "security_access.request start source_id=%s days=%s force_refresh=%s",
        source_id,
        days,
        force_refresh,
    )

    def _fetch_source() -> dict[str, object]:
        return security_access_group.data.fetch_data(days)

    sources = manager.load_page_data(
        "security_access",
        {source_id: _fetch_source},
        page_label="Security & Access Control",
        force_refresh=force_refresh,
        auto_refresh_stale=False,
        on_progress=lambda done, total: progress_caption.caption(f"Refreshed {done} of {total}"),
        data_ttl_seconds=600,  # 10 minutes
    )

    progress_caption.empty()
    data_age = manager.get_cache_age(source_id)
    logger.info(
        "security_access.request done source_id=%s force_refresh=%s data_age=%s elapsed=%.2fs",
        source_id,
        force_refresh,
        "none" if data_age is None else int(data_age),
        time.perf_counter() - request_started_at,
    )

    render_data_age_caption(data_age)

    return sources[source_id]


def render() -> None:
    """Render security and access control dashboard view."""
    cooldown_key = "dashboard_security_access_refresh_last_click"
    st.caption("Metrics are derived from recent connection records.")
    selected_days = st.selectbox(
        "Security window",
        options=[7, 14, 30, 60, 90],
        index=2,
        format_func=lambda value: f"Last {value} days",
        key="dashboard_security_access_days",
    )
    refresh_requested = st.button("Refresh", key="dashboard_security_access_refresh")

    force_refresh = _handle_refresh(cooldown_key, refresh_requested)
    render_refresh_warning(cooldown_key, cooldown_seconds=10)
    source_reader = _load_sources(int(selected_days), force_refresh)
    if source_reader is None:
        return

    render_widget_rows(
        [
            _with_render_timing(
                "standing_credentials",
                lambda: security_access_group.widget_standing_credentials.render(source_reader),
            ),
            _with_render_timing(
                "jit_credentials",
                lambda: security_access_group.widget_jit_credentials.render(source_reader),
            ),
            _with_render_timing(
                "break_glass_access",
                lambda: security_access_group.widget_break_glass_access.render(source_reader),
            ),
        ],
        max_per_row=2,
    )
