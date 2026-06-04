from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

if TYPE_CHECKING:
    from collections.abc import Callable


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def render(fetch_data: Callable[[int], dict[str, object]]) -> None:
    st.subheader("List of Certificate expired in N Days")
    st.caption("Certificates expiring within the selected upcoming day range.")

    selected_days = st.selectbox(
        "Expiration window",
        options=[7, 14, 30, 60, 90],
        index=2,
        format_func=lambda value: f"{value} days",
        key="dashboard_certificate_expiry_days",
    )

    data = fetch_data(int(selected_days))

    error_message = str(data.get("error", "")).strip()
    if error_message:
        st.error(error_message)
        return

    metric_cols = st.columns(2)
    with metric_cols[0]:
        st.metric("Expiring Certificates", _to_int(data.get("expiring_certificates", 0)))
    with metric_cols[1]:
        st.metric("Scanned Hosts", _to_int(data.get("scanned_hosts", 0)))

    rows = list(data.get("rows", []))
    if not rows:
        st.info(f"No certificates expiring in the next {selected_days} days.")
        st.caption(f"Last Updated: {data.get('updated_at', '-')}")
        return

    chart_data = pd.DataFrame(rows)
    if "Days Left" not in chart_data:
        st.info("No data available for chart.")
        st.caption(f"Last Updated: {data.get('updated_at', '-')}")
        return

    st.dataframe(chart_data, width="stretch", hide_index=True)
    st.caption(f"Showing top {len(chart_data)} certificate entries.")
    st.caption(f"Last Updated: {data.get('updated_at', '-')}")
