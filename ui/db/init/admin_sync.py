"""Synchronize required admin user in admin database."""

from __future__ import annotations

import os

from sqlalchemy import insert, select

from lib.clients.postgresql import use_database
from lib.database.models.admin.user import UserTable
from lib.database.models.admin.user_group import UserGroupTable
from ui.utils.password import hash_password


def sync_admin_user() -> dict[str, int]:
    """Ensure the default admin user exists.

    Requires ``UI_TMP_ADMIN_PASSWORD`` to be set and non-empty.
    """
    db = use_database("admin")

    with db.connection.begin():
        admin_group = db.connection.execute(
            select(UserGroupTable.c.id).where(UserGroupTable.c.name == "admin")
        ).fetchone()

        if admin_group is None:
            raise RuntimeError("Admin group does not exist. Run sync_admin_group first.")

        existing_admin = db.connection.execute(select(UserTable.c.id).where(UserTable.c.name == "admin")).fetchone()

        if existing_admin is not None:
            return {"inserted_admin_user": 0}

        raw_password = os.environ.get("UI_TMP_ADMIN_PASSWORD", "").strip()

        if not raw_password:
            raise RuntimeError("UI_TMP_ADMIN_PASSWORD must be set to create the admin user.")

        password_hash = hash_password(raw_password)

        insert_result = db.connection.execute(
            insert(UserTable),
            {
                "is_admin": True,
                "has_profile": True,
                "name": "admin",
                "display_name": "Administrator",
                "user_group_id": int(admin_group.id),
                "encrypted_password": password_hash,
            },
        )

        inserted_user = int(insert_result.rowcount or 0)

    return {"inserted_admin_user": inserted_user}
