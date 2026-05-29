"""Inputs for dynamic report options."""

from __future__ import annotations

import streamlit as st

from lib.utils.string import to_ui_message
from ui.services.report_service import get_ui_list_values


def render_dynamic_options(options: dict, subcommand_key: str, command: str = "", subcommand: str = "") -> dict:
    """Render option inputs from TOML option metadata.

    Args:
        options: Option metadata from config
        subcommand_key: Unique key for this subcommand
        command: The report command (e.g., "events") for ui_list resolution
        subcommand: The report subcommand (e.g., "query") for ui_list resolution

    Returns:
        Dict of form values keyed by option name
    """
    form_values = {}

    for opt_name, opt_config in options.items():
        if opt_name in ("ui_display", "ui_warning"):
            continue

        if not isinstance(opt_config, dict):
            continue

        if opt_config.get("ui_hidden", False):
            continue

        key = f"{subcommand_key}_{opt_name}"
        label = opt_name.replace("_", " ").capitalize()
        help_text = to_ui_message(opt_config.get("help", ""))
        required = opt_config.get("required", False)
        opt_type = opt_config.get("type", "string")
        action = opt_config.get("action", "")
        ui_list = opt_config.get("ui_list")

        label = f"{label} {'*' if required else ''}"

        # "store_true" is a presence flag: unchecked=False, checked=True.
        if action == "store_true" or opt_type == "boolean":
            form_values[opt_name] = st.checkbox(label, key=key, help=help_text)
        elif opt_type == "date":
            form_values[opt_name] = st.date_input(label, key=key, help=help_text, value=None)
        elif ui_list:
            # Render select + manual override for ui_list options
            form_values[opt_name] = _render_ui_list_input(
                label=label,
                help_text=help_text,
                key=key,
                command=command,
                subcommand=subcommand,
                ui_list_key=ui_list,
            )
        else:
            form_values[opt_name] = st.text_input(label, key=key, help=help_text)

    return form_values


def _render_ui_list_input(
    label: str,
    help_text: str,
    key: str,
    command: str,
    subcommand: str,
    ui_list_key: str,
) -> str | None:
    """Render a select input for ui_list options.

    If list fetch fails or is empty, falls back to plain text input.

    Args:
        label: Input label
        help_text: Help text
        key: Unique key for this input
        command: The report command for fetching list values
        subcommand: The report subcommand for fetching list values
        ui_list_key: The list key to fetch

    Returns:
        The selected value or None
    """
    # Fetch list values
    values, error = get_ui_list_values(command, subcommand, ui_list_key)

    # Fallback to plain text input on error or empty list
    if error or not values:
        if error:
            st.warning(f"Could not load suggestions: {error}")
        return st.text_input(label, key=key, help=help_text)

    # Render select with empty option at start
    select_options = [""] + values
    selected = st.selectbox(
        label,
        options=select_options,
        key=key,
        help=help_text,
    )

    return selected if selected else None
