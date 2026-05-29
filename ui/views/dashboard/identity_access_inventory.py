"""Identity and access inventory dashboard view."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import streamlit as st
from streamlit.logger import get_logger

from ui.components.widgets import (
    defined_network_targets,
    defined_privx_users,
    defined_target_accounts,
    defined_target_hosts,
)
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
            "identity_access.widget[%s] render took %.2fs",
            name,
            time.perf_counter() - started_at,
        )

    return _wrapped


def _handle_refresh(cooldown_key: str, refresh_requested: bool) -> bool:
    """Handle refresh request and return whether force-refresh is requested."""
    force_refresh = False

    if refresh_requested:
        if should_bounce_refresh(cooldown_key):
            logger.info("identity_access.refresh bounced reason=fetch_in_progress")
            return False

        can_refresh, remaining_seconds = get_refresh_cooldown_state(cooldown_key, cooldown_seconds=10)
        if can_refresh:
            set_refresh_warning_state(cooldown_key, visible=False)
            force_refresh = True
            mark_refresh(cooldown_key)
            logger.info("identity_access.refresh accepted cooldown_seconds=%s", 10)
        else:
            set_refresh_warning_state(cooldown_key, visible=True)
            logger.info("identity_access.refresh blocked remaining_seconds=%s", remaining_seconds)

    return force_refresh


def _load_sources(force_refresh: bool) -> dict[str, Callable[[], dict[str, object]]]:
    """Load identity and access sources through DataFetchManager."""
    manager = get_data_fetch_manager()
    source_ids = (
        "defined_privx_users",
        "defined_target_hosts",
        "defined_target_accounts",
        "defined_network_targets",
    )
    if not force_refresh and any(not manager.has_cache(source_id) for source_id in source_ids):
        st.info("No cached data yet. Click Refresh to load data.")
        render_data_age_caption(None)
        return {}

    progress_caption = st.empty()
    request_started_at = time.perf_counter()

    logger.info("identity_access.request start force_refresh=%s", force_refresh)

    sources = manager.load_page_data(
        "identity_access",
        {
            "defined_privx_users": defined_privx_users.data.fetch_data,
            "defined_target_hosts": defined_target_hosts.data.fetch_data,
            "defined_target_accounts": defined_target_accounts.data.fetch_data,
            "defined_network_targets": defined_network_targets.data.fetch_data,
        },
        page_label="Identity & Access Inventory",
        force_refresh=force_refresh,
        auto_refresh_stale=False,
        on_progress=lambda done, total: progress_caption.caption(f"Refreshed {done} of {total}"),
        data_ttl_seconds=600,  # 10 minutes
    )

    progress_caption.empty()
    cache_ages = [manager.get_cache_age(source_id) for source_id in sources]
    finite_cache_ages = [age for age in cache_ages if age is not None]
    logger.info(
        "identity_access.request done force_refresh=%s elapsed=%.2fs",
        force_refresh,
        time.perf_counter() - request_started_at,
    )

    render_data_age_caption(max(finite_cache_ages) if finite_cache_ages else None)

    return sources


def render() -> None:
    """Render identity and access inventory dashboard view."""
    cooldown_key = "dashboard_identity_access_refresh_last_click"
    st.caption("Inventory metrics are loaded through shared dashboard data cache.")

    refresh_requested = st.button("Refresh", key="dashboard_identity_access_refresh")
    force_refresh = _handle_refresh(cooldown_key, refresh_requested)
    render_refresh_warning(cooldown_key, cooldown_seconds=10)
    source_readers = _load_sources(force_refresh)
    if not source_readers:
        return

    render_widget_rows(
        [
            _with_render_timing(
                "defined_privx_users",
                lambda: defined_privx_users.widget.render(source_readers["defined_privx_users"]),
            ),
            _with_render_timing(
                "defined_target_hosts",
                lambda: defined_target_hosts.widget.render(source_readers["defined_target_hosts"]),
            ),
            _with_render_timing(
                "defined_target_accounts",
                lambda: defined_target_accounts.widget.render(source_readers["defined_target_accounts"]),
            ),
            _with_render_timing(
                "defined_network_targets",
                lambda: defined_network_targets.widget.render(source_readers["defined_network_targets"]),
            ),
        ],
        max_per_row=2,
    )
