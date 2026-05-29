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
    st.caption(str(data["description"]))

    error_message = str(data.get("error", "")).strip()
    if error_message:
        st.error(error_message)
        return

    counts = dict(data.get("counts", {}))
    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric("Password", _to_int(counts.get("Password", 0)))
    with metric_cols[1]:
        st.metric("OIDC", _to_int(counts.get("OIDC", 0)))
    with metric_cols[2]:
        st.metric("Key", _to_int(counts.get("Key", 0)))
    with metric_cols[3]:
        st.metric("Other", _to_int(counts.get("Other", 0)))

    rows = [
        {"Method": "Password", "Users": _to_int(counts.get("Password", 0))},
        {"Method": "OIDC", "Users": _to_int(counts.get("OIDC", 0))},
        {"Method": "Key", "Users": _to_int(counts.get("Key", 0))},
        {"Method": "Other", "Users": _to_int(counts.get("Other", 0))},
    ]
    chart_data = pd.DataFrame(rows)
    chart_series = pd.to_numeric(chart_data["Users"], errors="coerce")
    chart_series = chart_series.replace([float("inf"), float("-inf")], pd.NA).dropna()
    if chart_series.empty:
        st.info("No finite values available for chart.")
        st.caption(f"Total Users: {data.get('total_users', 0)}")
        st.caption(f"Last Updated: {data.get('updated_at', '-')}")
        return

    plot_data = chart_data.loc[chart_series.index].copy()
    plot_data["Users"] = chart_series.to_numpy()
    plot_data = plot_data.set_index("Method")
    st.bar_chart(plot_data["Users"], width="stretch", height=280)
    st.caption(f"Total Users: {data.get('total_users', 0)}")
    st.caption(f"Last Updated: {data.get('updated_at', '-')}")
