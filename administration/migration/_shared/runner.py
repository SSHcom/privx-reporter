from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

from sqlalchemy import text

from lib.clients.postgresql import db_execute, use_database

if TYPE_CHECKING:
    from datetime import datetime
    from types import ModuleType

ADMIN_DB = "admin"
DATA_DB = "data"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "_files"
_MIGRATION_FILENAME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-[A-Za-z0-9_-]+\.py$")
_VALID_TARGET_DBS = {ADMIN_DB, DATA_DB}


class MigrationScript(Protocol):
    def up(self) -> dict[str, list[str]]: ...

    def down(self) -> dict[str, list[str]]: ...


@dataclass(frozen=True)
class MigrationFile:
    name: str
    target_db: str
    up_statements: list[str]
    down_statements: list[str]


@dataclass(frozen=True)
class AppliedMigration:
    migration_name: str
    target_db: str
    applied_at: datetime


@dataclass(frozen=True)
class MigrationStatus:
    applied: list[AppliedMigration]
    pending: list[MigrationFile]


def ensure_migration_history_table() -> None:
    """Create migration history table on admin DB if it does not exist."""
    admin_db = use_database(ADMIN_DB)
    create_table_sql = text(
        """
        CREATE TABLE IF NOT EXISTS migration_history (
            id SERIAL PRIMARY KEY,
            migration_name VARCHAR NOT NULL,
            target_db VARCHAR NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (migration_name, target_db)
        )
        """
    )
    create_index_sql = text(
        "CREATE INDEX IF NOT EXISTS idx_migration_history_applied_at ON migration_history (applied_at)"
    )

    with admin_db.connection.begin():
        admin_db.connection.execute(create_table_sql)
        admin_db.connection.execute(create_index_sql)


def discover_migrations() -> list[MigrationFile]:
    """Load and validate migration files in lexical filename order."""
    migration_paths = sorted(path for path in MIGRATIONS_DIR.glob("*.py") if _is_valid_migration_filename(path.name))
    migrations: list[MigrationFile] = []
    for path in migration_paths:
        migrations.extend(_load_migration_file(path))
    return migrations


def apply_pending_migrations() -> list[MigrationFile]:
    """Apply all pending migrations and return what was applied."""
    ensure_migration_history_table()
    migrations = discover_migrations()
    applied_targets = {(migration.migration_name, migration.target_db) for migration in _get_applied_migrations()}

    newly_applied: list[MigrationFile] = []
    for migration in migrations:
        if (migration.name, migration.target_db) in applied_targets:
            continue

        db_execute(migration.up_statements, name=migration.target_db)
        _record_applied_migration(migration)
        newly_applied.append(migration)

    return newly_applied


def rollback_migrations(steps: int) -> list[str]:
    """Rollback latest applied migration files (across all target DBs)."""
    if steps < 1:
        raise ValueError("--steps must be a positive integer.")

    ensure_migration_history_table()
    known_migrations = {(migration.name, migration.target_db): migration for migration in discover_migrations()}
    applied_migrations = _get_applied_migrations()
    applied_in_reverse_order = list(reversed(applied_migrations))

    selected_migration_names: set[str] = set()
    for applied_migration in applied_in_reverse_order:
        selected_migration_names.add(applied_migration.migration_name)
        if len(selected_migration_names) == steps:
            break

    migrations_to_rollback = [
        applied_migration
        for applied_migration in applied_in_reverse_order
        if applied_migration.migration_name in selected_migration_names
    ]

    rolled_back_names: list[str] = []
    for applied_migration in migrations_to_rollback:
        migration = known_migrations.get((applied_migration.migration_name, applied_migration.target_db))
        if migration is None:
            raise ValueError(
                f"Applied migration '{applied_migration.migration_name}' for "
                f"database '{applied_migration.target_db}' is missing from migration files."
            )

        db_execute(migration.down_statements, name=applied_migration.target_db)
        _remove_applied_migration(applied_migration.migration_name, applied_migration.target_db)
        rolled_back_names.append(f"{applied_migration.migration_name} ({applied_migration.target_db})")

    return rolled_back_names


def get_migration_status() -> MigrationStatus:
    """Return applied and pending migration status."""
    ensure_migration_history_table()
    migrations = discover_migrations()
    applied = _get_applied_migrations()
    applied_targets = {(migration.migration_name, migration.target_db) for migration in applied}
    pending = [migration for migration in migrations if (migration.name, migration.target_db) not in applied_targets]
    return MigrationStatus(applied=applied, pending=pending)


def _is_valid_migration_filename(filename: str) -> bool:
    return bool(_MIGRATION_FILENAME_PATTERN.match(filename))


def _load_migration_file(path: Path) -> list[MigrationFile]:
    module = _load_module_from_path(path)
    migration_module = cast("MigrationScript", module)

    up_by_db = _validate_statements_by_db(path.name, "up", migration_module.up())
    down_by_db = _validate_statements_by_db(path.name, "down", migration_module.down())
    if set(up_by_db) != set(down_by_db):
        raise ValueError(f"Migration '{path.name}' must define same database keys in up() and down().")

    return [
        MigrationFile(
            name=path.stem,
            target_db=target_db,
            up_statements=up_by_db[target_db],
            down_statements=down_by_db[target_db],
        )
        for target_db in sorted(up_by_db)
    ]


def _validate_statements(migration_name: str, direction: str, statements: object) -> list[str]:
    if not isinstance(statements, list):
        raise ValueError(f"Migration '{migration_name}' {direction}() must return list[str].")
    if not statements:
        raise ValueError(f"Migration '{migration_name}' {direction}() returned an empty statement list.")
    for statement in statements:
        if not isinstance(statement, str) or not statement.strip():
            raise ValueError(f"Migration '{migration_name}' contains an invalid SQL statement in {direction}().")
    return statements


def _validate_statements_by_db(
    migration_name: str,
    direction: str,
    statements_by_db: object,
) -> dict[str, list[str]]:
    if not isinstance(statements_by_db, dict):
        raise ValueError(f"Migration '{migration_name}' {direction}() must return dict[str, list[str]].")
    if not statements_by_db:
        raise ValueError(f"Migration '{migration_name}' {direction}() returned an empty database map.")

    validated: dict[str, list[str]] = {}
    for target_db, statements in statements_by_db.items():
        if not isinstance(target_db, str) or target_db not in _VALID_TARGET_DBS:
            raise ValueError(
                f"Migration '{migration_name}' {direction}() contains invalid database key '{target_db}'. "
                f"Use only {ADMIN_DB!r} or {DATA_DB!r}."
            )
        validated[target_db] = _validate_statements(migration_name, direction, statements)

    return validated


def _load_module_from_path(path: Path) -> ModuleType:
    module_name = f"admin_migration_{path.stem.replace('-', '_')}"
    module_spec = importlib.util.spec_from_file_location(module_name, path)
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"Could not load migration module from '{path}'.")

    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _get_applied_migrations() -> list[AppliedMigration]:
    admin_db = use_database(ADMIN_DB)
    query = text(
        """
        SELECT migration_name, target_db, applied_at
        FROM migration_history
        ORDER BY applied_at ASC, id ASC
        """
    )

    with admin_db.connection.begin():
        rows = admin_db.connection.execute(query).mappings().all()

    return [
        AppliedMigration(
            migration_name=str(row["migration_name"]),
            target_db=str(row["target_db"]),
            applied_at=cast("datetime", row["applied_at"]),
        )
        for row in rows
    ]


def _record_applied_migration(migration: MigrationFile) -> None:
    admin_db = use_database(ADMIN_DB)
    insert_statement = text(
        """
        INSERT INTO migration_history (migration_name, target_db)
        VALUES (:migration_name, :target_db)
        """
    )
    with admin_db.connection.begin():
        admin_db.connection.execute(
            insert_statement,
            {
                "migration_name": migration.name,
                "target_db": migration.target_db,
            },
        )


def _remove_applied_migration(migration_name: str, target_db: str) -> None:
    admin_db = use_database(ADMIN_DB)
    delete_statement = text(
        "DELETE FROM migration_history WHERE migration_name = :migration_name AND target_db = :target_db"
    )
    with admin_db.connection.begin():
        admin_db.connection.execute(
            delete_statement,
            {
                "migration_name": migration_name,
                "target_db": target_db,
            },
        )
