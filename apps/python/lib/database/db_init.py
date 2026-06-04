"""Database initialization helpers for sync_server."""

import csv
import logging
from pathlib import Path

from sqlalchemy import func, insert, select, text

from administration.migration import apply as apply_migrations
from lib._shared.helpers import python_app_root
from lib.clients.postgresql import use_database
from lib.database.models.admin import AuditEventSyncTable

logger = logging.getLogger(__name__)


def _get_csv_paths() -> tuple[Path, Path]:
    administration_dir = python_app_root(Path(__file__)) / "administration"
    all_events = administration_dir / "events_all.csv"
    enabled_events = administration_dir / "events_enabled.csv"
    return all_events, enabled_events


def _read_enabled_event_codes(path: Path) -> set[int]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return {int(event_type["CODE"]) for event_type in reader}


def _seed_audit_event_sync_table() -> None:
    """Seed audit_event_sync from CSV when the table is empty."""
    db = use_database("admin")
    all_events_csv, enabled_events_csv = _get_csv_paths()
    enabled_event_codes = _read_enabled_event_codes(enabled_events_csv)

    with db.connection.begin():
        existing_rows = db.connection.execute(select(func.count()).select_from(AuditEventSyncTable)).scalar_one()
        if existing_rows > 0:
            return

        rows: list[dict[str, int | str | bool]] = []
        with all_events_csv.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for event_type in reader:
                code = int(event_type["CODE"])
                rows.append(
                    {
                        "code": code,
                        "enabled": code in enabled_event_codes,
                        "name": event_type["NAME"],
                        "severity": event_type["SEVERITY"],
                        "description": event_type["ORIGIN"],
                    }
                )

        if rows:
            db.connection.execute(insert(AuditEventSyncTable), rows)


def _connect(database_name: str, database_type: str) -> None:
    """Validate database connectivity."""
    try:
        database = use_database(database_name)
        logger.info("Successfully connected to %s", database_type)
        result = database.connection.execute(text("SELECT 1"))
        logger.info("%s test query result: %s", database_type, result.scalar())
        database.connection.commit()  # Commit any auto-begun transaction
    except Exception as e:
        logger.error("Error connecting to %s database: %s", database_name, e)
        raise


def init_databases() -> None:
    """Connect to databases and create required tables."""
    # Verify database connectivity
    _connect(database_name="admin", database_type="PostgreSQL 'admin' database")
    _connect(database_name="data", database_type="PostgreSQL w/TimescaleDB 'data' database")

    # Apply pending migrations
    migration_result = apply_migrations()

    if migration_result["error_message"] is not None:
        raise RuntimeError(migration_result["error_message"])

    _seed_audit_event_sync_table()
