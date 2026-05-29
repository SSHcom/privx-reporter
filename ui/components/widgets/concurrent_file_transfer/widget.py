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

    st.subheader("Concurrent File Transfer Sessions")
    st.caption("Live active file transfer sessions from PrivX connections.")

    error_message = str(data.get("error", "")).strip()
    if error_message:
        st.error(error_message)
        return

    session_count = _to_int(data.get("concurrent_file_transfer_sessions", 0))
    st.metric("File Transfer Sessions", session_count)

    type_counts_raw = data.get("file_transfer_type_counts", {})
    type_counts = type_counts_raw if isinstance(type_counts_raw, dict) else {}

    rows = [
        {"Type": "SFTP", "Sessions": _to_int(type_counts.get("SFTP", 0))},
        {"Type": "SCP", "Sessions": _to_int(type_counts.get("SCP", 0))},
        {"Type": "File Transfer", "Sessions": _to_int(type_counts.get("FILE_TRANSFER", 0))},
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
    plot_data = plot_data.set_index("Type")
    st.bar_chart(plot_data["Sessions"], width="stretch", height=280)
    st.caption(f"Last Updated: {data.get('updated_at', '-')}")
