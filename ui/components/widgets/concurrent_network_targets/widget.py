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


def render(fetch_data: Callable[[], dict[str, object]]) -> None:
    data = fetch_data()

    st.subheader("Concurrent Network Target Sessions")
    st.caption("Live active sessions by network target.")

    error_message = str(data.get("error", "")).strip()
    if error_message:
        st.error(error_message)
        return

    metrics_col1, metrics_col2 = st.columns(2)
    with metrics_col1:
        st.metric("Network Targets", _to_int(data.get("concurrent_network_targets", 0)))
    with metrics_col2:
        st.metric("Active Sessions", _to_int(data.get("active_sessions", 0)))

    rows = list(data.get("top_network_targets", []))
    if not rows:
        st.info("No active network target sessions right now.")
        st.caption(f"Last Updated: {data.get('updated_at', '-')}")
        return

    chart_data = pd.DataFrame(rows)
    if "Sessions" not in chart_data:
        st.info("No data available for chart.")
        st.caption(f"Last Updated: {data.get('updated_at', '-')}")
        return

    chart_series = pd.to_numeric(chart_data["Sessions"], errors="coerce")
    chart_series = chart_series.replace([float("inf"), float("-inf")], pd.NA).dropna()
    if chart_series.empty:
        st.info("No finite values available for chart.")
        st.caption(f"Last Updated: {data.get('updated_at', '-')}")
        return

    plot_data = chart_data.loc[chart_series.index].copy()
    plot_data["Sessions"] = chart_series.to_numpy()
    plot_data = plot_data.set_index("Network Target")
    st.bar_chart(plot_data["Sessions"], width="stretch", height=280)
    if "Target Key" in chart_data:
        st.dataframe(
            chart_data[["Network Target", "Target Key", "Sessions"]],
            width="stretch",
            hide_index=True,
        )
    st.caption(f"Last Updated: {data.get('updated_at', '-')}")
