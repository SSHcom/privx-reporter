import math

import pandas as pd
import streamlit as st


def display_datagrid_with_pagination(df: pd.DataFrame, scope_key: str = "default") -> None:
    key_base = f"datagrid_{scope_key}"
    page_key = f"{key_base}_page"
    page_size_key = f"{key_base}_page_size"
    total_rows = len(df)

    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    col1, space1, col2, space2, col3 = st.columns([1, 0.4, 1, 1, 1], vertical_alignment="bottom")

    with col1:
        if st.button("⬅ Prev", key=f"{key_base}_prev"):
            st.session_state[page_key] = max(1, int(st.session_state[page_key]) - 1)

    with space1:
        st.space("small")

    with col2:
        page_size = st.selectbox(
            "Rows per page",
            [10, 25, 50, 100],
            index=1,
            key=page_size_key,
            label_visibility="hidden",
            width="stretch",
        )
        total_pages = max(1, math.ceil(total_rows / page_size))

    with space2:
        st.space("small")

    with col3:
        if st.button("Next ➡", key=f"{key_base}_next"):
            st.session_state[page_key] = min(total_pages, int(st.session_state[page_key]) + 1)

    st.session_state[page_key] = max(1, min(int(st.session_state[page_key]), total_pages))

    start_idx = (int(st.session_state[page_key]) - 1) * page_size
    end_idx = min(start_idx + page_size, total_rows)
    page_df = df.iloc[start_idx:end_idx].reset_index(drop=True)
    page_df.index = page_df.index + 1  # start from 1

    st.dataframe(page_df, width="stretch")

    st.caption(
        f"Showing {start_idx + 1}–{min(end_idx, total_rows)} of {total_rows} rows "
        f"(Page {st.session_state[page_key]}/{total_pages})"
    )
