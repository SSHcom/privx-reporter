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

    st.subheader("Concurrent Client Connection Methods")
    st.caption("Live active connections by method: Native Client, Web, API.")

    error_message = str(data.get("error", "")).strip()
    if error_message:
        st.error(error_message)
        return

    method_counts = dict(data.get("client_method_counts", {}))

    method_cols = st.columns(3)
    with method_cols[0]:
        st.metric("Native Client", _to_int(method_counts.get("Native Client", 0)))
    with method_cols[1]:
        st.metric("Web", _to_int(method_counts.get("Web", 0)))
    with method_cols[2]:
        st.metric("API", _to_int(method_counts.get("API", 0)))

    rows = [
        {"Method": "Native Client", "Sessions": _to_int(method_counts.get("Native Client", 0))},
        {"Method": "Web", "Sessions": _to_int(method_counts.get("Web", 0))},
        {"Method": "API", "Sessions": _to_int(method_counts.get("API", 0))},
    ]
    chart_data = pd.DataFrame(rows)
    chart_series = pd.to_numeric(chart_data["Sessions"], errors="coerce")
    chart_series = chart_series.replace([float("inf"), float("-inf")], pd.NA).dropna()
    if chart_series.empty:
        st.info("No finite values available for chart.")
        st.caption(f"Last Updated: {data.get('updated_at', '-')}")
        return

    plot_data = chart_data.loc[chart_series.index].copy()
    plot_data["Sessions"] = chart_series.to_numpy()
    plot_data = plot_data.set_index("Method")
    st.bar_chart(plot_data["Sessions"], width="stretch", height=280)
    st.caption(f"Last Updated: {data.get('updated_at', '-')}")
