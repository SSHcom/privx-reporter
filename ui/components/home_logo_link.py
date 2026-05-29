from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st


def render_home_logo_link() -> bool:
    """Render a clickable logo that acts as the Home navigation action."""
    logo_path = Path(__file__).with_name("logo.png")
    logo_data = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    st.markdown(
        f"""
        <style>
        .st-key-home_logo_link button {{
            width: 220px;
            height: 90px;
            margin: 0 auto 0.5rem auto;
            padding: 0;
            border: none;
            border-radius: 0;
            color: transparent;
            background-color: transparent !important;
            background: center / contain no-repeat url("data:image/png;base64,{logo_data}");
            box-shadow: none;
        }}
        .st-key-home_logo_link button p {{
            display: none;
        }}
        .st-key-home_logo_link button:hover,
        .st-key-home_logo_link button:focus,
        .st-key-home_logo_link button:active {{
            color: transparent;
            background-color: transparent !important;
            background: center / contain no-repeat url("data:image/png;base64,{logo_data}");
            border: none;
            box-shadow: none;
            filter: brightness(0.95);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    return st.button("Home", key="home_logo_link")
