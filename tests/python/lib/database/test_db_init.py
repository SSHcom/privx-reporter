"""Tests for lib/database/db_init.py connectivity and initialization."""

from unittest.mock import MagicMock, call, patch

import pytest

import lib.database.db_init as db_init


@pytest.mark.unit
@pytest.mark.parametrize(
    ("database_name", "database_type"),
    [
        ("admin", "PostgreSQL admin database"),
        ("data", "TimescaleDB"),
    ],
)
@patch("lib.database.db_init.use_database")
def test_connect_runs_healthcheck_and_commit(
    mock_use_database: MagicMock,
    database_name: str,
    database_type: str,
) -> None:
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    db_init._connect(database_name=database_name, database_type=database_type)

    mock_use_database.assert_called_once_with(database_name)
    mock_db.connection.execute.assert_called_once()
    mock_db.connection.commit.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("database_name", "database_type"),
    [
        ("admin", "PostgreSQL admin database"),
        ("data", "TimescaleDB"),
    ],
)
@patch("lib.database.db_init.use_database")
def test_connect_propagates_errors(
    mock_use_database: MagicMock,
    database_name: str,
    database_type: str,
) -> None:
    mock_use_database.side_effect = RuntimeError("unavailable")
    with pytest.raises(RuntimeError, match="unavailable"):
        db_init._connect(database_name=database_name, database_type=database_type)


@pytest.mark.unit
@patch("lib.database.db_init._seed_audit_event_sync_table")
@patch("lib.database.db_init.apply_migrations")
@patch("lib.database.db_init._connect")
def test_init_databases_runs_migrations_and_seed(
    mock_connect: MagicMock, mock_apply_migrations: MagicMock, mock_seed: MagicMock
) -> None:
    mock_apply_migrations.return_value = {"error_message": None, "info_message": "ok"}

    db_init.init_databases()

    mock_connect.assert_has_calls(
        [
            call(database_name="admin", database_type="PostgreSQL 'admin' database"),
            call(database_name="data", database_type="PostgreSQL w/TimescaleDB 'data' database"),
        ]
    )
    mock_apply_migrations.assert_called_once_with()
    mock_seed.assert_called_once_with()


@pytest.mark.unit
@patch("lib.database.db_init._seed_audit_event_sync_table")
@patch("lib.database.db_init.apply_migrations")
@patch("lib.database.db_init._connect")
def test_init_databases_raises_when_migration_fails(
    mock_connect: MagicMock, mock_apply_migrations: MagicMock, mock_seed: MagicMock
) -> None:
    mock_apply_migrations.return_value = {"error_message": "migration failed", "info_message": None}

    with pytest.raises(RuntimeError, match="migration failed"):
        db_init.init_databases()

    assert mock_connect.call_count == 2
    mock_seed.assert_not_called()
