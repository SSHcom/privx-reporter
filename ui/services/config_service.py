from typing import Any

import streamlit as st
import toml


@st.cache_data
def get_report_config() -> dict[str, Any]:
    args_config_file = "../reports/config.toml"

    with open(args_config_file) as f:
        args_spec = toml.load(f)

    return args_spec
