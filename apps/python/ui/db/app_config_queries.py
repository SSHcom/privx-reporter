"""Database queries for app configuration values."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from lib.clients.postgresql import use_database
from lib.database.models.admin.app_config import AppConfigTable

if TYPE_CHECKING:
    from collections.abc import Mapping


def read_all_app_config_values() -> dict[str, str]:
    """Return all app config values as a setting_key -> value map."""
    db = use_database("admin")
    result = db.connection.execute(select(AppConfigTable.c.setting_key, AppConfigTable.c.value))
    return {str(row.setting_key): str(row.value) for row in result}


def upsert_app_config_values(values: Mapping[str, str]) -> None:
    """Insert or update multiple app config values by setting key."""
    if not values:
        return

    rows = [{"setting_key": key, "value": value} for key, value in values.items()]
    stmt = pg_insert(AppConfigTable).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[AppConfigTable.c.setting_key],
        set_={"value": stmt.excluded.value, "updated": func.now()},
    )

    db = use_database("admin")
    with db.connection.begin():
        db.connection.execute(stmt)
