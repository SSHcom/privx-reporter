"""Database queries for alternative report group views."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError

from lib.clients.postgresql import use_database
from lib.database.models.admin.alt_group import AltGroupTable
from lib.database.models.admin.alt_group_view import AltGroupViewTable
from lib.database.models.admin.report import ReportTable
from ui.db.user_group_queries import list_reports as list_all_reports

DeleteAltGroupViewResult = Literal["deleted", "not_found", "error"]


def create_alt_group_view(name: str) -> tuple[bool, str, int | None]:
    """Create a new alternative report grouping view."""
    stripped_name = name.strip()
    if not stripped_name:
        return False, "View name cannot be empty.", None

    db = use_database("admin")

    try:
        with db.connection.begin():
            result = db.connection.execute(
                insert(AltGroupViewTable).returning(AltGroupViewTable.c.id),
                {"name": stripped_name},
            )
            row = result.fetchone()
            view_id = row[0] if row else None

        return True, f"Report group view '{stripped_name}' created successfully.", view_id

    except IntegrityError:
        return False, f"Report group view '{stripped_name}' already exists.", None
    except Exception as e:
        return False, f"Failed to create report group view: {e}", None


def delete_alt_group_view(view_id: int) -> DeleteAltGroupViewResult:
    """Delete a view and all its report mappings."""
    db = use_database("admin")

    try:
        with db.connection.begin():
            view_row = db.connection.execute(
                select(AltGroupViewTable.c.id).where(AltGroupViewTable.c.id == view_id)
            ).fetchone()
            if view_row is None:
                return "not_found"

            db.connection.execute(delete(AltGroupTable).where(AltGroupTable.c.alt_group_view_id == view_id))
            db.connection.execute(delete(AltGroupViewTable).where(AltGroupViewTable.c.id == view_id))
        return "deleted"
    except Exception:
        return "error"


def list_alt_group_views() -> list[dict[str, Any]]:
    """Return all alternative group views ordered by name."""
    db = use_database("admin")

    with db.connection.begin():
        result = db.connection.execute(
            select(AltGroupViewTable.c.id, AltGroupViewTable.c.name).order_by(AltGroupViewTable.c.name)
        )
        rows = result.fetchall()
        columns = result.keys()
        return [dict(zip(columns, row)) for row in rows]


def add_report_to_alt_group(
    alt_group_view_id: int,
    group_name: str,
    report_id: int,
) -> tuple[bool, str]:
    """Assign a report to a named group within a view."""
    stripped_group_name = group_name.strip()
    if not stripped_group_name:
        return False, "Group name cannot be empty."

    db = use_database("admin")
    try:
        with db.connection.begin():
            db.connection.execute(
                insert(AltGroupTable),
                {
                    "alt_group_view_id": alt_group_view_id,
                    "group_name": stripped_group_name,
                    "report_id": report_id,
                },
            )
        return True, "Report assignment saved."
    except IntegrityError:
        return False, "This report is already assigned to that group in this view."
    except Exception as e:
        return False, f"Failed to save report assignment: {e}"


def add_reports_to_alt_group(
    alt_group_view_id: int,
    group_name: str,
    report_ids: list[int],
) -> tuple[bool, str]:
    """Assign multiple reports to a named group within a view in one transaction."""
    stripped_group_name = group_name.strip()
    if not stripped_group_name:
        return False, "Group name cannot be empty."
    if not report_ids:
        return False, "Select at least one report."

    payload = [
        {
            "alt_group_view_id": alt_group_view_id,
            "group_name": stripped_group_name,
            "report_id": report_id,
        }
        for report_id in report_ids
    ]

    db = use_database("admin")
    try:
        with db.connection.begin():
            db.connection.execute(insert(AltGroupTable), payload)
        return True, "Report assignments saved."
    except IntegrityError:
        return False, "One or more selected reports are already assigned in this view."
    except Exception as e:
        return False, f"Failed to save report assignments: {e}"


def remove_report_from_alt_group(alt_group_id: int) -> None:
    """Remove a report-group assignment by mapping row ID."""
    db = use_database("admin")

    with db.connection.begin():
        db.connection.execute(delete(AltGroupTable).where(AltGroupTable.c.id == alt_group_id))


def get_groups_for_view(alt_group_view_id: int) -> list[dict[str, Any]]:
    """Return report assignments for a view, including report names."""
    db = use_database("admin")

    with db.connection.begin():
        result = db.connection.execute(
            select(
                AltGroupTable.c.id,
                AltGroupTable.c.group_name,
                ReportTable.c.id.label("report_id"),
                ReportTable.c.group_name.label("report_group_name"),
                ReportTable.c.report_name,
            )
            .select_from(AltGroupTable)
            .join(ReportTable, AltGroupTable.c.report_id == ReportTable.c.id)
            .where(AltGroupTable.c.alt_group_view_id == alt_group_view_id)
            .order_by(
                AltGroupTable.c.group_name,
                ReportTable.c.group_name,
                ReportTable.c.report_name,
            )
        )
        rows = result.fetchall()
        columns = result.keys()
        return [dict(zip(columns, row)) for row in rows]


def list_reports() -> list[dict[str, Any]]:
    """Reuse shared report listing query used by admin pages."""
    return list_all_reports()
