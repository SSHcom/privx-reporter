from __future__ import annotations

from typing import TYPE_CHECKING

import altair as alt
import pandas as pd
import streamlit as st

if TYPE_CHECKING:
    from collections.abc import Callable


def render(fetch_data: Callable[[], dict[str, object]], *, top_n: int | None = None) -> None:
    data = fetch_data()

    selected_top_n = int(top_n) if top_n is not None else int(data.get("top_n", 10))
    st.subheader(f"Top {selected_top_n} Target Accounts")
    st.caption("Source: Synced DB (requires Sync Server)")
    rows = list(data.get("top_target_accounts", []))
    if not rows:
        st.info("No target account data available.")
        st.caption(f"Last Updated: {data.get('updated_at', '-')}")
        return

    chart_data = pd.DataFrame(rows)
    chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X("Target Account:N", sort="-y"),
            y=alt.Y("Connections:Q"),
            tooltip=[
                alt.Tooltip("Target Account:N"),
                alt.Tooltip("Connections:Q"),
                alt.Tooltip("Host Names:N"),
                alt.Tooltip("Host IPs:N"),
                alt.Tooltip("Host UUIDs:N"),
                alt.Tooltip("Host Detail:N"),
            ],
        )
        .properties(height=280)
    )
    st.altair_chart(chart, width="stretch")
    st.caption("Hover bars to view host details.")
    st.dataframe(
        chart_data[["Target Account", "Host Names", "Host IPs", "Host UUIDs", "Connections"]],
        width="stretch",
        hide_index=True,
    )
    st.caption(f"Last Updated: {data.get('updated_at', '-')}")
