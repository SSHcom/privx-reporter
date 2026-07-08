from typing import Any

import streamlit as st
import toml

from lib._shared.helpers import python_app_root
from ui.db.app_config_queries import read_all_app_config_values


@st.cache_data
def _load_required_ui_privx_keys() -> tuple[str, ...]:
    config_path = python_app_root() / "lib" / "app_config.toml"
    with open(config_path, encoding="utf-8") as f:
        spec = toml.load(f)

    sections = spec.get("sections", {})
    if not isinstance(sections, dict):
        return ()

    required_keys: list[str] = []
    for section_name in ("ui", "privx"):
        section_data = sections.get(section_name, {})
        if not isinstance(section_data, dict):
            continue
        vars_data = section_data.get("vars", {})
        if not isinstance(vars_data, dict):
            continue
        for key, field_data in vars_data.items():
            if not isinstance(field_data, dict):
                continue
            if bool(field_data.get("optional", False)):
                continue
            required_keys.append(str(key))

    return tuple(sorted(set(required_keys)))


def get_missing_required_ui_privx_values() -> list[str]:
    required_keys = _load_required_ui_privx_keys()
    if not required_keys:
        return []

    try:
        db_values = read_all_app_config_values()
    except Exception:
        return list(required_keys)
    missing_keys = [key for key in required_keys if not str(db_values.get(key, "")).strip()]
    return sorted(missing_keys)


def has_required_ui_privx_values_configured() -> bool:
    return len(get_missing_required_ui_privx_values()) == 0


@st.cache_data
def get_report_config() -> dict[str, Any]:
    args_config_file = "../reports/config.toml"

    with open(args_config_file) as f:
        args_spec = toml.load(f)

    return args_spec
