from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

if TYPE_CHECKING:
    from collections.abc import Callable


def render(fetch_data: Callable[[], dict[str, object]], *, top_n: int | None = None) -> None:
    data = fetch_data()

    selected_top_n = int(top_n) if top_n is not None else int(data.get("top_n", 10))
    st.subheader(f"Top {selected_top_n} PrivX Users")
    st.caption("Source: Synced DB (requires Sync Server)")
    rows = list(data.get("top_privx_users", []))
    if not rows:
        st.info("No user connection data available.")
        st.caption(f"Last Updated: {data.get('updated_at', '-')}")
        return

    chart_data = pd.DataFrame(rows).set_index("User")
    st.bar_chart(chart_data["Connections"], width="stretch", height=280)
    st.caption(f"Last Updated: {data.get('updated_at', '-')}")
