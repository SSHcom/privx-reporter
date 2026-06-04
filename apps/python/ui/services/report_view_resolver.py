"""Resolve and cache sidebar report views for the current user."""

from __future__ import annotations

from collections import defaultdict
from typing import TypedDict

import streamlit as st

from ui.db.alt_group_queries import get_groups_for_view, list_alt_group_views
from ui.services import report_service
from ui.services.config_service import get_report_config
from ui.services.permissions import is_admin
from ui.services.session import keys


class ResolvedReport(TypedDict):
    """Single report entry in a resolved view."""

    primary: str
    subcommand: str


class ResolvedGroup(TypedDict):
    """Group node in a resolved view."""

    name: str
    reports: list[ResolvedReport]


class ResolvedView(TypedDict):
    """Top-level report view used by sidebar rendering."""

    id: int | None
    name: str
    groups: list[ResolvedGroup]


def invalidate_report_view_cache() -> None:
    """Invalidate session-cached resolved report views."""
    st.session_state[keys.RESOLVED_REPORT_VIEWS] = None


def prime_report_view_cache() -> None:
    """Resolve and cache report views for current user if missing."""
    _ = get_resolved_report_views()


def get_resolved_report_views() -> list[ResolvedView]:
    """Return resolved report views, filtered for current user access."""
    cached = st.session_state.get(keys.RESOLVED_REPORT_VIEWS)
    if cached is not None:
        return cached

    report_config = get_report_config()
    user_is_admin = is_admin()
    viewable_reports = set(report_service.get_viewable_reports())
    resolved_views: list[ResolvedView] = []

    default_groups: list[ResolvedGroup] = []
    for primary, config in report_config.items():
        visible_reports = [
            {"primary": primary, "subcommand": subcommand}
            for subcommand in config.get("subcommands", {})
            if user_is_admin or (primary, subcommand) in viewable_reports
        ]
        if visible_reports:
            default_groups.append({"name": primary, "reports": visible_reports})

    if default_groups:
        resolved_views.append({"id": None, "name": "Default", "groups": default_groups})

    for view in list_alt_group_views():
        rows_by_group: dict[str, list[ResolvedReport]] = defaultdict(list)
        for row in get_groups_for_view(view["id"]):
            if user_is_admin or (row["report_group_name"], row["report_name"]) in viewable_reports:
                rows_by_group[row["group_name"]].append(
                    {
                        "primary": row["report_group_name"],
                        "subcommand": row["report_name"],
                    }
                )

        groups = [{"name": group_name, "reports": reports} for group_name, reports in rows_by_group.items() if reports]
        if groups:
            resolved_views.append({"id": view["id"], "name": view["name"], "groups": groups})

    st.session_state[keys.RESOLVED_REPORT_VIEWS] = resolved_views
    return resolved_views
