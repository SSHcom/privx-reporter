"""Superadmin-only page for editing app configuration values."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import streamlit as st
import toml

from lib._shared.helpers import python_app_root
from lib.clients.privx import clear_privx_client_cache
from lib.env import EnvConfig
from lib.service.env_source import reloadEnv
from ui.components.sidebar import render_sidebar
from ui.constants import APP_CONFIG_PAGE_TITLE
from ui.db.app_config_queries import read_all_app_config_values, upsert_app_config_values
from ui.db.user_group_queries import list_user_groups
from ui.services.page_bootstrap import setup_page
from ui.services.permissions import is_admin, is_superadmin_username
from ui.services.session import keys

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}
_WIDGET_PREFIX = "app_config_field_"
_SAVE_FEEDBACK_KEY = "admin_app_config_save_feedback"
_OIDC_ICONS_DIR = python_app_root() / "ui" / "assets" / "icons" / "oidc"


def _list_oidc_icons() -> list[str]:
    """Return sorted list of available OIDC icon filenames."""
    if not _OIDC_ICONS_DIR.is_dir():
        return []
    return sorted(f.name for f in _OIDC_ICONS_DIR.iterdir() if f.suffix == ".svg")


def _get_svg_aspect_ratio(svg_content: str) -> float:
    """Extract aspect ratio (width/height) from SVG viewBox or width/height attrs. Default 1.0 for square."""
    # Try viewBox first
    match = re.search(r'viewBox=["\']([^"\']+)["\']', svg_content)
    if match:
        parts = match.group(1).split()
        if len(parts) == 4:
            try:
                w, h = float(parts[2]), float(parts[3])
                if h > 0:
                    return w / h
            except ValueError:
                pass
    # Fallback to width/height attributes
    width_match = re.search(r'\bwidth=["\'](\d+(?:\.\d+)?)["\']', svg_content)
    height_match = re.search(r'\bheight=["\'](\d+(?:\.\d+)?)["\']', svg_content)
    if width_match and height_match:
        try:
            w, h = float(width_match.group(1)), float(height_match.group(1))
            if h > 0:
                return w / h
        except ValueError:
            pass
    return 1.0


@dataclass(frozen=True)
class AppConfigFieldSpec:
    key: str
    label: str
    description: str
    section_id: str
    section_title: str
    section_order: int
    field_order: int
    field_type: str
    widget: str
    default: str
    validator: str | None
    optional: bool


def _sort_order(value: object, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _load_schema() -> list[AppConfigFieldSpec]:
    config_path = python_app_root() / "lib" / "app_config.toml"
    with open(config_path, encoding="utf-8") as fh:
        spec = toml.load(fh)

    sections = spec.get("sections", {})
    if not isinstance(sections, dict):
        return []

    fields: list[AppConfigFieldSpec] = []
    for section_id, section_data in sections.items():
        if not isinstance(section_data, dict):
            continue

        section_title = str(section_data.get("title", section_id))
        section_order = _sort_order(section_data.get("order"))
        vars_data = section_data.get("vars", {})
        if not isinstance(vars_data, dict):
            continue

        for key, raw_field in vars_data.items():
            if not isinstance(raw_field, dict):
                continue

            fields.append(
                AppConfigFieldSpec(
                    key=str(key),
                    label=str(raw_field.get("label", key)),
                    description=str(raw_field.get("description", "")),
                    section_id=section_id,
                    section_title=section_title,
                    section_order=section_order,
                    field_order=_sort_order(raw_field.get("order")),
                    field_type=str(raw_field.get("type", "string")),
                    widget=str(raw_field.get("widget", "text")),
                    default=str(raw_field.get("default", "")),
                    validator=str(raw_field.get("validate")) if raw_field.get("validate") is not None else None,
                    optional=bool(raw_field.get("optional", False)),
                )
            )

    fields.sort(key=lambda item: (item.section_order, item.field_order, item.key))
    return fields


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in _TRUE_VALUES


def _resolve_value(
    key: str,
    default: str,
    db_values: dict[str, str],
    *,
    allow_env_fallback: bool = True,
) -> tuple[str, str]:
    if key in db_values:
        return str(db_values[key]), "db"
    if allow_env_fallback:
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value, "env"
    return default, "default"


def _normalize_output_value(field: AppConfigFieldSpec, raw_value: object) -> str:
    if field.widget == "checkbox":
        # Handle string boolean values from db (e.g. "true", "false")
        if isinstance(raw_value, str):
            return "true" if _parse_bool(raw_value) else "false"
        return "true" if bool(raw_value) else "false"
    value = str(raw_value).strip()
    if field.validator == "oidc_icon" and value == "(none)":
        return ""
    return value


def _validate_value(
    field: AppConfigFieldSpec,
    value: str,
    values_by_key: dict[str, str],
    allowed_user_groups: set[str],
) -> str | None:
    raw = value.strip()
    validator = field.validator or ""

    if not raw:
        if validator == "non_empty_when_slot_enabled":
            slot_match = re.fullmatch(r"OIDC_(\d+)_STATE_SECRET", field.key)
            slot = slot_match.group(1) if slot_match else None
            enabled_key = f"OIDC_{slot}_ENABLED" if slot else None
            if enabled_key and _parse_bool(values_by_key.get(enabled_key, "false")):
                return f"{field.label} is required when OIDC provider {slot} is enabled."
        elif not field.optional and validator in {"non_empty", "positive_int", "sync_triple"}:
            return f"{field.label} cannot be empty."
        return None

    if validator == "non_empty":
        if not raw:
            return f"{field.label} cannot be empty."
        return None

    if validator == "positive_int":
        if not raw.isdigit() or int(raw) <= 0:
            return f"{field.label} must be a positive integer."
        return None

    if validator == "port":
        if not raw.isdigit() or not (1 <= int(raw) <= 65535):
            return f"{field.label} must be a valid TCP port (1-65535)."
        return None

    if validator == "hour_utc":
        if not raw.isdigit() or not (0 <= int(raw) <= 23):
            return f"{field.label} must be an integer between 0 and 23."
        return None

    if validator == "bool":
        lowered = raw.lower()
        if lowered not in _TRUE_VALUES and lowered not in _FALSE_VALUES:
            return f"{field.label} must be one of: true, false, 1, 0, yes, no, on, off."
        return None

    if validator == "sync_triple":
        parts = [part.strip() for part in raw.split(",")]
        if len(parts) != 3 or any(not part.isdigit() for part in parts):
            return f"{field.label} must be three comma-separated integers (e.g. 5,10,15)."
        if any(int(part) <= 0 for part in parts):
            return f"{field.label} values must be positive integers."
        return None

    if validator == "backup_config":
        parts = [part.strip() for part in raw.split(",")]
        if len(parts) != 4:
            return f"{field.label} must be '<enabled>,<target>,<interval-minutes>,<snapshots>' (e.g. true,all,720,5)."
        enabled, target, interval_raw, snapshots_raw = parts
        if enabled not in {"true", "false"}:
            return f"{field.label}: enabled must be 'true' or 'false'."
        if target not in {"admin", "data", "all"}:
            return f"{field.label}: target must be one of 'admin', 'data', or 'all'."
        if not interval_raw.isdigit() or int(interval_raw) < 60:
            return f"{field.label}: interval-minutes must be a number >= 60."
        if not snapshots_raw.isdigit() or int(snapshots_raw) < 1:
            return f"{field.label}: snapshots must be a number >= 1."
        return None

    if validator == "json_object":
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return f"{field.label} must be valid JSON."
        if not isinstance(parsed, dict):
            return f"{field.label} must be a JSON object."
        return None

    if validator == "url":
        parsed = urlparse(raw)
        if not parsed.scheme or not parsed.netloc:
            return f"{field.label} must be a valid URL including scheme and host."
        return None

    if validator == "user_group":
        if raw.lower() in {"admin", "superadmin"}:
            return f"{field.label} cannot be 'admin' or 'superadmin'."
        if allowed_user_groups and raw not in allowed_user_groups:
            return f"{field.label} must be one of: {', '.join(sorted(allowed_user_groups))}."
        return None

    if validator == "oidc_icon":
        if not raw:
            return None
        available_icons = _list_oidc_icons()
        if raw not in available_icons:
            return f"{field.label} must be one of the available icons or empty."
        return None

    if validator == "non_empty_when_slot_enabled":
        slot_match = re.fullmatch(r"OIDC_(\d+)_STATE_SECRET", field.key)
        slot = slot_match.group(1) if slot_match else None
        enabled_key = f"OIDC_{slot}_ENABLED" if slot else None
        if enabled_key and _parse_bool(values_by_key.get(enabled_key, "false")) and not raw:
            return f"{field.label} is required when OIDC provider {slot} is enabled."
        return None

    return None


def _main() -> None:
    setup_page(page_title=APP_CONFIG_PAGE_TITLE, show_sidebar=False)

    current_username = st.session_state.get(keys.USERNAME)
    if not is_admin() or not is_superadmin_username(current_username):
        st.error("Access denied. This page is restricted to superadmin.")
        st.stop()

    render_sidebar()
    st.title("App Configuration")
    get_env_source = getattr(EnvConfig, "get_env_source", None)
    if callable(get_env_source):
        env_source = str(get_env_source()).strip().lower()
    else:
        env_source = os.getenv("ENV_SOURCE", "env").strip().lower()
    if env_source not in {"env", "db"}:
        env_source = "env"
    if env_source != "db":
        st.info(
            "Configuration source is set to environment variables "
            f"(`ENV_SOURCE={env_source}`). This form is disabled. "
            "Set `ENV_SOURCE=db` to manage values from this page."
        )
        st.caption("Current runtime uses environment variables, with defaults as fallback.")
        return

    try:
        schema = _load_schema()
    except Exception as exc:
        st.error(f"Failed to load app config schema: {exc}")
        st.stop()

    if not schema:
        st.warning("No configurable fields were found in app_config.toml.")
        st.stop()

    try:
        db_values = read_all_app_config_values()
    except Exception as exc:
        st.error(f"Failed to read app config values: {exc}")
        st.stop()

    try:
        group_rows = list_user_groups()
        allowed_user_groups = {
            str(row.get("name", "")).strip()
            for row in group_rows
            if str(row.get("name", "")).strip().lower() not in {"admin", "superadmin"}
        }
    except Exception:
        allowed_user_groups = set()

    current_values: dict[str, str] = {}
    source_by_key: dict[str, str] = {}
    for field in schema:
        resolved_value, source = _resolve_value(
            field.key,
            field.default,
            db_values,
            allow_env_fallback=False,
        )
        current_values[field.key] = resolved_value
        source_by_key[field.key] = source

    missing_mandatory_keys = [
        field.key for field in schema if not field.optional and source_by_key.get(field.key) != "db"
    ]
    if missing_mandatory_keys:
        st.warning(f"Missing value(s) for {len(missing_mandatory_keys)} mandatory setting(s)")

    with st.form("admin_app_config_form"):
        current_section_id = None
        for field in schema:
            if current_section_id != field.section_id:
                current_section_id = field.section_id
                st.subheader(field.section_title)

            initial_value = current_values[field.key]
            widget_key = f"{_WIDGET_PREFIX}{field.key}"
            source = source_by_key[field.key]
            source_help = field.description

            if field.widget == "textarea":
                st.text_area(
                    field.label,
                    value=initial_value,
                    key=widget_key,
                    help=source_help,
                )
            elif field.widget == "checkbox":
                st.checkbox(
                    field.label,
                    value=_parse_bool(initial_value),
                    key=widget_key,
                    help=source_help,
                )
            elif field.widget == "password":
                st.text_input(
                    field.label,
                    value=initial_value,
                    key=widget_key,
                    type="password",
                    help=source_help,
                )
            elif field.widget == "select" and field.validator == "user_group" and allowed_user_groups:
                options = sorted(allowed_user_groups)
                if initial_value and initial_value not in options:
                    options = [initial_value, *options]
                default_index = options.index(initial_value) if initial_value in options else 0
                st.selectbox(
                    field.label,
                    options=options,
                    index=default_index,
                    key=widget_key,
                    help=source_help,
                )
            elif field.widget == "select" and field.validator == "oidc_icon":
                icon_files = _list_oidc_icons()
                options = ["(none)", *icon_files]
                # Only use initial_value if it's a valid existing icon file
                current = initial_value if initial_value in icon_files else "(none)"
                default_index = options.index(current) if current in options else 0

                # Build expander label with current selection preview
                current_label = "None" if current == "(none)" else current.removesuffix(".svg")
                with st.expander(f"{field.label}: {current_label}", expanded=False):
                    if source_help:
                        st.caption(source_help)

                    # Show available icons as visual preview grid
                    if icon_files:
                        num_cols = min(len(icon_files), 4)
                        cols = st.columns(num_cols)
                        for i, icon_file in enumerate(icon_files):
                            with cols[i % num_cols]:
                                icon_path = _OIDC_ICONS_DIR / icon_file
                                if icon_path.exists():
                                    with open(icon_path, encoding="utf-8") as f:
                                        svg_content = f.read()
                                    label = icon_file.removesuffix(".svg")
                                    # Size container based on SVG aspect ratio (fixed height, dynamic width)
                                    icon_height = 32
                                    aspect = _get_svg_aspect_ratio(svg_content)
                                    icon_width = min(int(icon_height * aspect), 120)  # cap at 120px
                                    # Inject CSS to make SVG fill its container
                                    svg_styled = re.sub(
                                        r"<svg([^>]*)>",
                                        r'<svg\1 style="width:100%;height:100%;">',
                                        svg_content,
                                        count=1,
                                    )
                                    st.markdown(
                                        f'<div style="text-align:center;padding:8px;">'
                                        f'<div style="width:{icon_width}px;height:{icon_height}px;margin:0 auto;">'
                                        f"{svg_styled}</div>"
                                        f"<small>{label}</small></div>",
                                        unsafe_allow_html=True,
                                    )

                    st.selectbox(
                        "Select",
                        options=options,
                        index=default_index,
                        key=widget_key,
                        format_func=lambda x: "None" if x == "(none)" else x.removesuffix(".svg"),
                        label_visibility="collapsed",
                    )
            else:
                st.text_input(
                    field.label,
                    value=initial_value,
                    key=widget_key,
                    help=source_help,
                )

            if source != "db":
                st.markdown(
                    "<span style='color:#d32f2f;'>Not configured</span>",
                    unsafe_allow_html=True,
                )

        save_feedback = st.session_state.pop(_SAVE_FEEDBACK_KEY, None)
        if isinstance(save_feedback, tuple) and len(save_feedback) == 2:
            level, message = save_feedback
            if level == "success":
                st.success(message)
            elif level == "info":
                st.info(message)
            elif level == "error":
                st.error(message)

        submitted = st.form_submit_button("Save Configuration")

    if not submitted:
        return

    submitted_values: dict[str, str] = {}
    for field in schema:
        widget_key = f"{_WIDGET_PREFIX}{field.key}"
        submitted_values[field.key] = _normalize_output_value(field, st.session_state.get(widget_key, ""))

    validation_errors: list[str] = []
    for field in schema:
        error = _validate_value(field, submitted_values[field.key], submitted_values, allowed_user_groups)
        if error:
            validation_errors.append(error)

    if validation_errors:
        for error in validation_errors:
            st.error(error)
        return

    changed_values: dict[str, str] = {}
    for field in schema:
        new_value = submitted_values[field.key]
        if field.key not in db_values:
            changed_values[field.key] = new_value
            continue
        old_value = _normalize_output_value(field, db_values.get(field.key, ""))
        if new_value != old_value:
            changed_values[field.key] = new_value

    if not changed_values:
        st.session_state[_SAVE_FEEDBACK_KEY] = ("info", "No changes to save.")
        st.rerun()

    try:
        upsert_app_config_values(changed_values)
    except Exception as exc:
        st.session_state[_SAVE_FEEDBACK_KEY] = ("error", f"Failed to save app config values: {exc}")
        st.rerun()

    # DB-backed env values are cached per process; refresh them after save.
    reloadEnv()
    clear_privx_client_cache()

    st.session_state[_SAVE_FEEDBACK_KEY] = ("success", "Configuration was updated.")
    st.rerun()


_main()
