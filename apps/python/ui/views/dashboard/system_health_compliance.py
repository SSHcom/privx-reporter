"""System health and compliance dashboard view."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from ui.components.widgets import system_health_compliance_group
from ui.services.data_fetch_manager import get_data_fetch_manager
from ui.views.dashboard import (
    get_refresh_cooldown_state,
    mark_refresh,
    render_data_age_caption,
    render_refresh_warning,
    set_refresh_warning_state,
    should_bounce_refresh,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def _handle_refresh(cooldown_key: str, refresh_requested: bool) -> bool:
    force_refresh = False
    if refresh_requested:
        if should_bounce_refresh(cooldown_key):
            return False
        can_refresh, _ = get_refresh_cooldown_state(cooldown_key, cooldown_seconds=10)
        if can_refresh:
            set_refresh_warning_state(cooldown_key, visible=False)
            force_refresh = True
            mark_refresh(cooldown_key)
        else:
            set_refresh_warning_state(cooldown_key, visible=True)
    return force_refresh


def _render_certificate_section(fetch_data: Callable[[], dict[str, object]]) -> None:
    """Render certificate expiry and status breakdown."""
    data = fetch_data()

    error = str(data.get("error", "")).strip()
    if error:
        st.error(error)
        return

    total = int(data.get("total_certificates", 0))
    expiring = list(data.get("expiring_soon", []))
    expired = list(data.get("recently_expired", []))
    status_breakdown = dict(data.get("status_breakdown", {}))

    # Status breakdown as metric cards
    st.subheader("Certificate Status Breakdown")
    if status_breakdown:
        cols = st.columns(len(status_breakdown), gap="small")
        for col, (status, count) in zip(cols, sorted(status_breakdown.items())):
            with col:
                with st.container(border=True):
                    st.metric(status.replace("CERT_", ""), count)
    st.caption(f"Total certificates: {total}")

    # Expiring soon
    st.subheader(f"Expiring Within 30 Days ({len(expiring)})")
    if expiring:
        df = pd.DataFrame(expiring)
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.success("No certificates expiring within 30 days.")

    # Recently expired
    st.subheader(f"Expired Within Last 7 Days ({len(expired)})")
    if expired:
        df = pd.DataFrame(expired)
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.success("No certificates expired in the last 7 days.")

    st.caption(f"Last updated: {data.get('updated_at', '-')}")


def render() -> None:
    """Render the System Health and Compliance dashboard view."""
    cooldown_key = "dashboard_system_health_compliance_refresh_last_click"

    refresh_requested = st.button("Refresh", key="dashboard_system_health_compliance_refresh")
    force_refresh = _handle_refresh(cooldown_key, refresh_requested)
    render_refresh_warning(cooldown_key, cooldown_seconds=10)

    manager = get_data_fetch_manager()
    source_id = "certificate_status"

    if not force_refresh and not manager.has_cache(source_id):
        st.info("No cached data yet. Click Refresh to load data.")
        render_data_age_caption(None)
        return

    sources = manager.load_page_data(
        "system_health_compliance",
        {source_id: system_health_compliance_group.data.fetch_certificate_data},
        page_label="System Health & Compliance",
        force_refresh=force_refresh,
        auto_refresh_stale=False,
        data_ttl_seconds=600,
    )

    render_data_age_caption(manager.get_cache_age(source_id))

    _render_certificate_section(sources[source_id])
