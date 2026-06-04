import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import toml

from lib._report.generator import generate, get_list
from lib.env import EnvConfig
from lib.utils.string import to_ui_message
from ui.bootstrap import configure_logging
from ui.db.user_group_queries import get_viewable_report_names
from ui.services.cache_service import get_cached_logger, get_cached_privx_client
from ui.services.permissions import UserPermissions, is_admin
from ui.services.session import keys

logger = get_cached_logger()


def get_viewable_reports() -> list[tuple[str, str]]:
    """Get viewable reports for the current user, cached in session state.

    Returns:
        A list of `(group_name, report_name)` tuples.
        Returns an empty list if the user is not authenticated or unknown.
    """
    # Return cached value if available
    cached = st.session_state.get(keys.VIEWABLE_REPORTS)
    if cached is not None:
        return cached

    # Get current username
    username = st.session_state.get(keys.USERNAME)
    if not username:
        # No username - return empty list (deny-by-default)
        st.session_state[keys.VIEWABLE_REPORTS] = []
        return []

    # Fetch from database
    reports = get_viewable_report_names(username)
    st.session_state[keys.VIEWABLE_REPORTS] = reports
    return reports


def can_access_report(primary: str, subcommand: str) -> bool:
    """Check if the current user can access a specific report.

    Uses the cached viewable reports from session state.

    Args:
        primary: The report group (e.g., "access", "roles")
        subcommand: The specific report (e.g., "hosts", "members")

    Returns:
        True if the user can access this report, False otherwise.
    """
    if is_admin():
        return True

    viewable = get_viewable_reports()

    # If empty list, user has no access
    if not viewable:
        return False

    # Check if this report is in the viewable list
    for group_name, report_name in viewable:
        if group_name == primary and report_name == subcommand:
            return True

    return False


def get_ui_list_values(command: str, subcommand: str, list_key: str) -> tuple[list[str], str | None]:
    """Fetch UI list values for a report command, subcommand, and list key.

    Access is allowed if the user has access to the specific subcommand.

    Args:
        command: The report command (e.g., "events")
        subcommand: The report subcommand (e.g., "query")
        list_key: The list key to retrieve (e.g., "event_names")

    Returns:
        Tuple of (values, error_message). Values will be empty list on error.
    """
    # Check if user has access to this specific report
    if not can_access_report(command, subcommand):
        return [], "You do not have access to this report."

    logger.info(f"Fetching UI list: {command} / {subcommand} / {list_key}")

    try:
        response = get_list(command, subcommand, list_key)
        return response.values, response.error_message
    except Exception as e:
        logger.error(f"Error fetching UI list: {e}")
        return [], f"Error fetching list values: {str(e)}"


def get_user_output_dir() -> Path:
    """Return the report output directory for the current user.

    The path is ``<base_output_dir>/<group>/<username>``. The directory is
    created if it does not already exist.
    """
    base_dir = Path(EnvConfig.get_report_out_dir())
    permissions = st.session_state.get(keys.USER_PERMISSIONS)
    group = permissions.group if permissions else "default"
    username = st.session_state.get(keys.USERNAME) or "unknown"
    user_dir = base_dir / group / username
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


@dataclass(frozen=True)
class ReportFile:
    """A report file with its originating group."""

    path: Path
    group: str  # empty string for non-admin views
    username: str  # empty string for non-admin views


def _collect_files_from_dir(
    directory: Path,
    group_label: str,
    username_label: str,
    report_config: dict[str, Any],
) -> dict[str, dict[str, list[ReportFile]]]:
    """Scan *directory* and return files grouped by primary/subcommand.

    Only subcommands the current user can access are included.
    *group_label* is attached to each :class:`ReportFile`.
    """
    if not directory.exists():
        return {}

    all_paths = list(directory.iterdir())
    result: dict[str, dict[str, list[ReportFile]]] = {}

    for primary, config in report_config.items():
        for subcommand in config.get("subcommands", {}).keys():
            if not can_access_report(primary, subcommand):
                continue

            file_pattern = re.compile(
                rf"^{re.escape(primary)}\.{re.escape(subcommand)}(\.[^.]+)*\.\d{{8}}_\d{{6}}\.(csv|json)$"
            )
            matching = [
                ReportFile(path=p, group=group_label, username=username_label)
                for p in all_paths
                if p.is_file() and file_pattern.match(p.name)
            ]
            if matching:
                result.setdefault(primary, {}).setdefault(subcommand, []).extend(matching)

    return result


def get_user_report_files(
    report_config: dict[str, Any],
    permissions: UserPermissions | None,
) -> dict[str, dict[str, list[ReportFile]]]:
    """Return report files for the current user's group only (group label is ``""``).."""
    user_dir = get_user_output_dir()
    _ = permissions
    return _collect_files_from_dir(user_dir, "", "", report_config)


def get_all_report_files(
    report_config: dict[str, Any],
    permissions: UserPermissions | None,
) -> dict[str, dict[str, list[ReportFile]]]:
    """Return report files across all group/user directories (admin view).

    Each :class:`ReportFile` carries the originating group and username.
    """
    base_dir = Path(EnvConfig.get_report_out_dir())
    merged: dict[str, dict[str, list[ReportFile]]] = {}
    _ = permissions

    if not base_dir.exists():
        return merged

    group_dirs = sorted(
        (d for d in base_dir.iterdir() if d.is_dir()),
        key=lambda d: (d.name != "admin", d.name),
    )

    for child in group_dirs:
        group_name = child.name
        user_dirs = sorted((d for d in child.iterdir() if d.is_dir()), key=lambda d: d.name)
        for user_dir in user_dirs:
            username = user_dir.name
            partial = _collect_files_from_dir(user_dir, group_name, username, report_config)
            for primary, subs in partial.items():
                for subcommand, files in subs.items():
                    merged.setdefault(primary, {}).setdefault(subcommand, []).extend(files)

    return merged


def run_report(
    primary: str,
    subcommand: str,
    form_values: dict | None = None,
    display_to_page: bool = False,
    json_output: bool = False,
    selected_fields: list[str] | None = None,
) -> tuple[str | None, pd.DataFrame | None, dict | None, str | None, str | None]:
    """
    Run a report and return the results.

    Returns:
        tuple: (file_path, dataframe, json_data, error_message, info_message)
    """
    # Re-apply logging for each report run. Streamlit reruns can keep mutated
    # logger levels/handlers between interactions.
    configure_logging(force=True)

    if not can_access_report(primary, subcommand):
        return None, None, None, "You do not have access to this report.", None

    logger.info(f"Running report: {primary} / {subcommand}")
    if form_values:
        logger.info(f"Query params: {form_values}")
    else:
        logger.info("No query params")
    if display_to_page:
        logger.info("Display to page: True")
    if json_output:
        logger.info("JSON output: True")
    if selected_fields:
        logger.info(f"Selected fields: {selected_fields}")

    api = get_cached_privx_client()

    args_config_file = "../reports/config.toml"
    with open(args_config_file) as f:
        config = toml.load(f)

    args = argparse.Namespace()
    args.command = primary
    args.subcommand = subcommand
    args.to_json = json_output

    user_group_id: str | None = None
    if not is_admin():
        session_group_id = st.session_state.get(keys.USER_GROUP_ID)
        if session_group_id in (None, ""):
            return (
                None,
                None,
                None,
                "Program error: User group is missing (this should not happen).",
                None,
            )
        user_group_id = str(session_group_id)

    # For list commands, always write to file (UI needs file to read and display)
    # The UI will then read the file and display it in the DataFrame viewer
    if primary == "list":
        args.to_file = True

    if form_values:
        for key, value in form_values.items():
            if value:
                setattr(args, key, value)

    if selected_fields:
        args.fields = ",".join(selected_fields)

    # Direct report output to the group/user-specific subdirectory.
    user_dir = get_user_output_dir()
    original_env = os.environ.get("REPORT_OUT_DIR")
    os.environ["REPORT_OUT_DIR"] = str(user_dir)
    try:
        result = generate(api, args, config, user_group_id=user_group_id)
    finally:
        if original_env is None:
            os.environ.pop("REPORT_OUT_DIR", None)
        else:
            os.environ["REPORT_OUT_DIR"] = original_env

    df = None
    json_data = None

    if display_to_page and result["report_path"]:
        json_source = form_values.get("json_source", False) if form_values else False
        if json_source or json_output:
            with open(result["report_path"]) as f:
                json_data = json.load(f)
        else:
            df = pd.read_csv(result["report_path"])

    return (
        result["report_path"],
        df,
        json_data,
        to_ui_message(result.get("error_message")),
        to_ui_message(result.get("info_message")),
    )
