from __future__ import annotations

from typing import TYPE_CHECKING

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

    st.subheader("Connections marked as Usual by UEBA")
    st.caption("Source: Synced DB (requires Sync Server)")
    st.metric("Usual Connections", _to_int(data.get("connections_ueba_usual", 0)))
    st.caption(f"Last Updated: {data.get('updated_at', '-')}")
