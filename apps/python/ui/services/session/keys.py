"""Canonical Streamlit session-state keys used by the UI."""

from __future__ import annotations

AUTHENTICATED = "authenticated"
USERNAME = "username"
DISPLAY_NAME = "display_name"
USER_ID = "user_id"
USER_GROUP_ID = "user_group_id"
HAS_PROFILE = "has_profile"
USER_GROUP = "user_group"
USER_PERMISSIONS = "user_permissions"
VIEWABLE_REPORTS = "viewable_reports"
RESOLVED_REPORT_VIEWS = "resolved_report_views"
SELECTED_PRIMARY = "selected_primary"
SELECTED_SUBCOMMAND = "selected_subcommand"
SELECTED_ALT_GROUP_VIEW = "selected_alt_group_view"
DASHBOARD_VIEW = "dashboard_view"
SESSION_TOKEN = "session_token"


def report_result_key(subcommand_key: str) -> str:
    """Return the key that stores report execution results."""
    return f"report_result_{subcommand_key}"


def expand_files_key(scope_key: str) -> str:
    """Return the key that controls report-file expander state."""
    return f"expand_files_{scope_key}"
