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

    st.subheader(str(data["label"]))
    st.caption("Source: Synced DB (requires Sync Server)")
    st.caption(str(data["description"]))

    error_message = str(data.get("error", "")).strip()
    if error_message:
        st.error(error_message)
        return

    st.metric("Collected Errors", _to_int(data.get("total_errors", 0)))

    rows = list(data.get("top_error_events", []))
    if rows:
        chart_data = pd.DataFrame(rows)
        if "Count" not in chart_data:
            st.info("No data available for chart.")
            st.caption(f"Last Updated: {data.get('updated_at', '-')}")
            return

        chart_series = pd.to_numeric(chart_data["Count"], errors="coerce")
        chart_series = chart_series.replace([float("inf"), float("-inf")], pd.NA).dropna()
        if chart_series.empty:
            st.info("No finite values available for chart.")
            st.caption(f"Last Updated: {data.get('updated_at', '-')}")
            return

        plot_data = chart_data.loc[chart_series.index].copy()
        plot_data["Count"] = chart_series.to_numpy()
        plot_data = plot_data.set_index("Event")
        st.bar_chart(plot_data["Count"], width="stretch", height=320)
    else:
        st.info("No collected system errors found.")

    st.caption(f"Last Updated: {data.get('updated_at', '-')}")
