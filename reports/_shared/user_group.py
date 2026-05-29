"""Shared user-group lookup helpers."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from lib.clients.postgresql import use_database
from lib.database.models.admin.user import UserTable
from lib.database.models.admin.user_group import UserGroupTable


@dataclass(frozen=True)
class UserGroup:
    """Resolved user-group details for a specific username."""

    id: int
    name: str
    access_groups: list[str]


def _parse_access_groups(access_groups_raw: object) -> list[str]:
    if not isinstance(access_groups_raw, str):
        return [""]

    parsed = [item.strip() for item in access_groups_raw.split(",") if item.strip()]
    return parsed or [""]


def get_user_group(username: str) -> UserGroup | None:
    """Return the user's group details, or ``None`` when user is unknown."""
    normalized_username = str(username).strip()
    if not normalized_username:
        return None

    db = use_database("admin")

    with db.connection.begin():
        row = db.connection.execute(
            select(
                UserGroupTable.c.id,
                UserGroupTable.c.name,
                UserGroupTable.c.access_groups,
            )
            .select_from(UserTable)
            .join(UserGroupTable, UserTable.c.user_group_id == UserGroupTable.c.id)
            .where(UserTable.c.name == normalized_username)
        ).fetchone()

    if row is None:
        return None

    return UserGroup(
        id=row[0],
        name=row[1],
        access_groups=_parse_access_groups(row[2]),
    )


def get_user_group_by_id(group_id: int) -> UserGroup | None:
    """Return group details by group id, or ``None`` when unknown."""
    db = use_database("admin")

    with db.connection.begin():
        row = db.connection.execute(
            select(
                UserGroupTable.c.id,
                UserGroupTable.c.name,
                UserGroupTable.c.access_groups,
            ).where(UserGroupTable.c.id == group_id)
        ).fetchone()

    if row is None:
        return None

    return UserGroup(
        id=row[0],
        name=row[1],
        access_groups=_parse_access_groups(row[2]),
    )
