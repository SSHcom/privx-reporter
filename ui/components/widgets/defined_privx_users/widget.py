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

    total_users = _to_int(data.get("total_defined_privx_users", 0))
    local_users = _to_int(data.get("local_users", 0))
    non_local_users = _to_int(data.get("non_local_users", 0))

    top_cols = st.columns(3)
    with top_cols[0]:
        st.metric("Defined PrivX Users", total_users)
    with top_cols[1]:
        st.metric("Local Users", local_users)
    with top_cols[2]:
        st.metric("Non-Local Users", non_local_users)

    users_raw = data.get("users", [])
    users = users_raw if isinstance(users_raw, list) else []
    users_shown = _to_int(data.get("users_shown", len(users)))

    if users:
        with st.expander(f"Show User List ({users_shown} of {total_users})", expanded=False):
            st.caption(f"Showing first {users_shown} users")
            users_df = pd.DataFrame(users)
            st.dataframe(users_df, width="stretch", hide_index=True)

    st.caption(f"Last Updated: {data.get('updated_at', '-')}")
