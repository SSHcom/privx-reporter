"""Field picker used by report forms."""

from __future__ import annotations

import streamlit as st


def render_field_selector(fields: dict, subcommand_key: str) -> list[str]:
    """Render the field selector in an expander and return selected field names."""
    field_list = []
    default_selected = []

    for field_name, field_config in fields.items():
        if isinstance(field_config, str):
            parts = field_config.split("|", 1)
            is_selected = parts[0].lower() == "true"
            label = parts[1] if len(parts) > 1 else field_name.replace("_", " ").capitalize()
        elif isinstance(field_config, list):
            parts = field_config[0].split("|", 1) if field_config else "true|".split("|", 1)
            is_selected = parts[0].lower() == "true"
            label = parts[1] if len(parts) > 1 else field_name.replace("_", " ").capitalize()
        else:
            is_selected = True
            label = field_name.replace("_", " ").capitalize()

        field_list.append((field_name, label))
        if is_selected:
            default_selected.append(field_name)

    total_fields = len(field_list)
    selected_fields = st.multiselect(
        "Select Fields",
        options=[name for name, _ in field_list],
        format_func=lambda x: next(label for name, label in field_list if name == x),
        default=default_selected,
        key=f"{subcommand_key}_fields",
    )

    selected_count = len(selected_fields)
    if selected_count == total_fields:
        st.caption(f":white_check_mark: All {total_fields} fields selected")
    else:
        st.caption(f":information_source: {selected_count}/{total_fields} fields selected")

    return selected_fields
