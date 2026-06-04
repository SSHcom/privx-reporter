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

    st.subheader(str(data["label"]))
    st.caption(str(data["description"]))

    error_message = str(data.get("error", "")).strip()
    if error_message:
        st.error(error_message)
        return

    st.metric("Defined Target Accounts", _to_int(data.get("total_defined_target_accounts", 0)))
    st.caption(f"Last Updated: {data.get('updated_at', '-')}")
