"""Database queries for user group management."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError

from lib.clients.postgresql import use_database
from lib.database.models.admin.report import ReportTable
from lib.database.models.admin.user import UserTable
from lib.database.models.admin.user_group import UserGroupTable
from lib.database.models.admin.user_group_report import UserGroupReportTable

DeleteUserGroupResult = Literal["deleted", "blocked_due_to_assignments", "not_found", "error"]
DEFAULT_ACCESS_GROUP = "Default"
ADMIN_GROUP_NAME = "admin"


def _normalize_access_groups_for_create(name: str, access_groups: str | None) -> str | None:
    """Normalize access groups for group creation.

    Rules:
    - Admin group keeps ``NULL`` access groups.
    - Non-admin groups always include ``Default``.
    """
    if name.strip().lower() == ADMIN_GROUP_NAME:
        return None

    raw_value = access_groups.strip() if access_groups is not None else ""
    parsed = [item.strip() for item in raw_value.split(",") if item.strip()]

    has_default = any(item.lower() == DEFAULT_ACCESS_GROUP.lower() for item in parsed)
    if not has_default:
        parsed.append(DEFAULT_ACCESS_GROUP)

    return ",".join(parsed) if parsed else DEFAULT_ACCESS_GROUP


def list_user_groups() -> list[dict[str, Any]]:
    """Return all user groups ordered by name.

    Returns:
        A list of dictionaries with group id and name.
    """
    db = use_database("admin")

    with db.connection.begin():
        result = db.connection.execute(
            select(
                UserGroupTable.c.id,
                UserGroupTable.c.name,
                UserGroupTable.c.access_groups,
            ).order_by(UserGroupTable.c.name)
        )

        rows = result.fetchall()
        columns = result.keys()

        return [dict(zip(columns, row)) for row in rows]


def list_reports() -> list[dict[str, Any]]:
    """Return all reports ordered by group_name and report_name for stable rendering.

    Returns:
        A list of dictionaries with report id, group_name, and report_name.
    """
    db = use_database("admin")

    with db.connection.begin():
        result = db.connection.execute(
            select(
                ReportTable.c.id,
                ReportTable.c.group_name,
                ReportTable.c.report_name,
            ).order_by(ReportTable.c.group_name, ReportTable.c.report_name)
        )

        rows = result.fetchall()
        columns = result.keys()

        return [dict(zip(columns, row)) for row in rows]


def get_report_ids_for_group(user_group_id: int) -> set[int]:
    """Fetch report IDs currently included in a user group.

    Args:
        user_group_id: The ID of the user group.

    Returns:
        A set of report IDs that are members of the group.
    """
    db = use_database("admin")

    with db.connection.begin():
        result = db.connection.execute(
            select(UserGroupReportTable.c.report_id).where(UserGroupReportTable.c.user_group_id == user_group_id)
        )

        return {row[0] for row in result.fetchall()}


def include_report_in_group(user_group_id: int, report_id: int) -> None:
    """Add a report to a user group (idempotent).

    If the mapping already exists, this is a no-op.

    Args:
        user_group_id: The ID of the user group.
        report_id: The ID of the report to include.
    """
    db = use_database("admin")

    with db.connection.begin():
        # Check if mapping already exists (idempotent)
        existing = db.connection.execute(
            select(UserGroupReportTable.c.id).where(
                UserGroupReportTable.c.user_group_id == user_group_id,
                UserGroupReportTable.c.report_id == report_id,
            )
        ).fetchone()

        if existing is None:
            db.connection.execute(
                insert(UserGroupReportTable),
                {"user_group_id": user_group_id, "report_id": report_id},
            )


def exclude_report_from_group(user_group_id: int, report_id: int) -> None:
    """Remove a report from a user group (idempotent).

    If the mapping does not exist, this is a no-op.

    Args:
        user_group_id: The ID of the user group.
        report_id: The ID of the report to exclude.
    """
    db = use_database("admin")

    with db.connection.begin():
        db.connection.execute(
            delete(UserGroupReportTable).where(
                UserGroupReportTable.c.user_group_id == user_group_id,
                UserGroupReportTable.c.report_id == report_id,
            )
        )


def create_user_group(
    name: str,
    access_groups: str | None = None,
) -> tuple[bool, str, int | None]:
    """Create a new user group.

    Args:
        name: The name for the new user group.
        access_groups: Optional CSV string defining access group filters.

    Returns:
        A tuple of (success, message, group_id) where success is True if the group
        was created, message contains a success or error description, and group_id
        is the ID of the created group (or None on failure).
    """
    # Validate non-empty name
    stripped_name = name.strip()
    if not stripped_name:
        return False, "Group name cannot be empty.", None

    normalized_access_groups = _normalize_access_groups_for_create(stripped_name, access_groups)

    db = use_database("admin")

    try:
        with db.connection.begin():
            result = db.connection.execute(
                insert(UserGroupTable).returning(UserGroupTable.c.id),
                {
                    "name": stripped_name,
                    "access_groups": normalized_access_groups,
                },
            )
            row = result.fetchone()
            group_id = row[0] if row else None

        return True, f"User group '{stripped_name}' created successfully.", group_id

    except IntegrityError:
        return False, f"User group '{stripped_name}' already exists.", None
    except Exception as e:
        return False, f"Failed to create user group: {e}", None


def update_user_group_access_groups(user_group_id: int, access_groups: str) -> bool:
    """Update the access group CSV filter string for a user group.

    Args:
        user_group_id: The ID of the user group to update.
        access_groups: CSV list of access group filters.

    Returns:
        True if a row was updated, False otherwise.
    """
    db = use_database("admin")
    stripped_access_groups = access_groups.strip()

    with db.connection.begin():
        result = db.connection.execute(
            update(UserGroupTable)
            .where(UserGroupTable.c.id == user_group_id)
            .values(access_groups=stripped_access_groups or None)
        )

    return result.rowcount > 0


def delete_user_group(group_id: int) -> DeleteUserGroupResult:
    """Delete a user group by ID, enforcing that no users are assigned.

    Performs an assignment check and only deletes when the assignment count is zero.
    On success, related ``user_group_report`` mappings are removed in the same
    transaction before the group itself is deleted.

    Args:
        group_id: The ID of the user group to delete.

    Returns:
        One of:
        - ``"deleted"`` - group was successfully removed.
        - ``"blocked_due_to_assignments"`` - one or more users are assigned; no rows mutated.
        - ``"not_found"`` - no group with the given ID exists.
        - ``"error"`` - an unexpected exception occurred.
    """
    db = use_database("admin")

    try:
        with db.connection.begin():
            # Verify the group exists
            group_row = db.connection.execute(
                select(UserGroupTable.c.id).where(UserGroupTable.c.id == group_id)
            ).fetchone()

            if group_row is None:
                return "not_found"

            # Check for assigned users (assignment-aware guard)
            assigned_count = db.connection.execute(
                select(func.count()).select_from(UserTable).where(UserTable.c.user_group_id == group_id)
            ).scalar()

            if assigned_count and assigned_count > 0:
                return "blocked_due_to_assignments"

            # Remove report mappings before deleting the group
            db.connection.execute(delete(UserGroupReportTable).where(UserGroupReportTable.c.user_group_id == group_id))

            # Delete the group
            db.connection.execute(delete(UserGroupTable).where(UserGroupTable.c.id == group_id))

        return "deleted"

    except Exception:
        return "error"


def get_viewable_report_names(username: str) -> list[tuple[str, str]]:
    """Resolve report names accessible by the given username.

    Looks up the user by username, finds their user group, and returns
    the list of reports (group_name, report_name) mapped to that group.

    Args:
        username: The login username to look up.

    Returns:
        A list of `(group_name, report_name)` tuples.
        Returns an empty list if the user does not exist or has no mapped reports.

    Note:
        This implements deny-by-default behavior: unknown users get no reports.
        TODO: Integrate with session management when implemented.
    """
    if not username:
        return []

    db = use_database("admin")

    with db.connection.begin():
        # Find the user and their user group
        user_result = db.connection.execute(
            select(UserTable.c.user_group_id).where(UserTable.c.name == username)
        ).fetchone()

        if user_result is None:
            # User not found - return empty list (deny-by-default)
            return []

        user_group_id = user_result[0]

        # Get all reports mapped to this user's user group
        result = db.connection.execute(
            select(ReportTable.c.group_name, ReportTable.c.report_name)
            .select_from(UserGroupReportTable)
            .join(ReportTable, UserGroupReportTable.c.report_id == ReportTable.c.id)
            .where(UserGroupReportTable.c.user_group_id == user_group_id)
            .order_by(ReportTable.c.group_name, ReportTable.c.report_name)
        )

        rows = result.fetchall()
        return [(row[0], row[1]) for row in rows]
