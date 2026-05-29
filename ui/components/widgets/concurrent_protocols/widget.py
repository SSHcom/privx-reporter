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

    st.subheader("Concurrent Sessions by Protocol")
    st.caption("Live active PrivX sessions split by connection protocol.")

    error_message = str(data.get("error", "")).strip()
    if error_message:
        st.error(error_message)
        return

    protocol_counts = dict(data.get("protocol_counts", {}))
    rows = [
        {"Protocol": "RDP", "Sessions": _to_int(protocol_counts.get("RDP", 0))},
        {"Protocol": "SSH", "Sessions": _to_int(protocol_counts.get("SSH", 0))},
        {"Protocol": "Web", "Sessions": _to_int(protocol_counts.get("Web", 0))},
        {"Protocol": "DB", "Sessions": _to_int(protocol_counts.get("DB", 0))},
        {"Protocol": "VNC", "Sessions": _to_int(protocol_counts.get("VNC", 0))},
    ]

    st.metric("Active Sessions", _to_int(data.get("active_sessions", 0)))

    chart_data = pd.DataFrame(rows)
    chart_series = pd.to_numeric(chart_data["Sessions"], errors="coerce")
    chart_series = chart_series.replace([float("inf"), float("-inf")], pd.NA).dropna()
    if chart_series.empty:
        st.info("No finite values available for chart.")
        st.caption(f"Last Updated: {data.get('updated_at', '-')}")
        return

    plot_data = chart_data.loc[chart_series.index].copy()
    plot_data["Sessions"] = chart_series.to_numpy()
    plot_data = plot_data.set_index("Protocol")
    st.bar_chart(plot_data["Sessions"], width="stretch", height=280)
    st.caption(f"Last Updated: {data.get('updated_at', '-')}")
