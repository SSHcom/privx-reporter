"""Database schema parity tests for SQLAlchemy table contracts."""

import os
from collections.abc import Iterable

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.sql.schema import Table
from sqlalchemy.sql.type_api import TypeEngine

import lib.clients.postgresql as postgres_client
import lib.database.models.admin  # noqa: F401
import lib.database.models.sync  # noqa: F401
from administration.migration import apply as apply_migrations
from lib.clients.postgresql import use_database
from lib.database.models.meta import admin_db_metadata, data_db_metadata

TEST_DATABASE_ENV = {
    "DB_ADMIN_HOST": "localhost",
    "DB_ADMIN_PORT": "5446",
    "DB_ADMIN_NAME": "reporter_test",
    "DB_ADMIN_USER": "postgres",
    "DB_ADMIN_PASSWORD": "postgres",
    "DB_ADMIN_SSL_MODE": "off",
    "DB_DATA_HOST": "localhost",
    "DB_DATA_PORT": "5446",
    "DB_DATA_NAME": "reporter_test",
    "DB_DATA_USER": "postgres",
    "DB_DATA_PASSWORD": "postgres",
    "DB_DATA_SSL_MODE": "off",
}


@pytest.fixture(scope="module", autouse=True)
def prepare_migrated_schema() -> Iterable[None]:
    """Ensure the test database is reachable and migrated before parity checks."""
    original_env = _set_test_database_env()
    _reset_cached_database_clients()
    _assert_database_connectivity("admin")
    _assert_database_connectivity("data")

    migration_result = apply_migrations()
    if migration_result["error_message"] is not None:
        pytest.fail(
            "Failed to apply migrations before schema parity checks. "
            f"Migration error: {migration_result['error_message']}",
            pytrace=False,
        )
    yield
    _restore_test_database_env(original_env)
    _reset_cached_database_clients()


@pytest.mark.database
def test_admin_models_match_database_schema() -> None:
    """All admin SQLAlchemy table definitions match reflected admin DB schema."""
    _assert_metadata_matches_database(admin_db_metadata.sorted_tables, "admin")


@pytest.mark.database
def test_data_models_match_database_schema() -> None:
    """All data SQLAlchemy table definitions match reflected data DB schema."""
    _assert_metadata_matches_database(data_db_metadata.sorted_tables, "data")


def _assert_database_connectivity(database_name: str) -> None:
    try:
        database = use_database(database_name)
        probe_result = database.connection.execute(text("SELECT 1")).scalar()
        if database.connection.in_transaction():
            database.connection.commit()
    except Exception as exc:
        pytest.fail(
            (
                f"Could not connect to '{database_name}' database for schema parity tests.\n"
                "Start the database test container with:\n"
                "  docker compose -f docker-compose-test.yml up -d\n"
                "The schema parity tests use fixed test-database settings\n"
                "(localhost:5446, database=reporter_test, user=postgres, password=postgres).\n"
                f"Original error: {exc!r}"
            ),
            pytrace=False,
        )

    assert probe_result == 1, f"Connectivity probe for '{database_name}' returned {probe_result!r}, expected 1."


def _assert_metadata_matches_database(tables: Iterable[Table], database_name: str) -> None:
    inspector = inspect(use_database(database_name).engine)
    for table in tables:
        _assert_table_columns(table, inspector)
        _assert_table_column_types(table, inspector)
        _assert_table_nullable(table, inspector)
        _assert_table_primary_key(table, inspector)


def _assert_table_columns(table: Table, inspector: Inspector) -> None:
    db_columns = {column["name"] for column in inspector.get_columns(table.name)}
    model_columns = {column.name for column in table.columns}
    assert model_columns == db_columns, (
        f"Column mismatch for table '{table.name}': "
        f"missing in DB={sorted(model_columns - db_columns)}, unexpected in DB={sorted(db_columns - model_columns)}"
    )


def _assert_table_column_types(table: Table, inspector: Inspector) -> None:
    db_columns = {column["name"]: column for column in inspector.get_columns(table.name)}
    for model_column in table.columns:
        db_column = db_columns[model_column.name]
        model_family = _type_family_name(model_column.type)
        db_family = _type_family_name(db_column["type"])
        assert model_family == db_family, (
            f"Type mismatch for '{table.name}.{model_column.name}': model={model_family}, database={db_family}"
        )


def _assert_table_nullable(table: Table, inspector: Inspector) -> None:
    db_columns = {column["name"]: column for column in inspector.get_columns(table.name)}
    for model_column in table.columns:
        db_column = db_columns[model_column.name]
        db_nullable = bool(db_column.get("nullable"))
        assert bool(model_column.nullable) == db_nullable, (
            f"Nullability mismatch for '{table.name}.{model_column.name}': "
            f"model={model_column.nullable}, database={db_nullable}"
        )


def _assert_table_primary_key(table: Table, inspector: Inspector) -> None:
    db_pk = set(inspector.get_pk_constraint(table.name).get("constrained_columns") or [])
    model_pk = {column.name for column in table.primary_key.columns}
    assert model_pk == db_pk, (
        f"Primary key mismatch for table '{table.name}': model={sorted(model_pk)}, database={sorted(db_pk)}"
    )


def _type_family_name(sql_type: TypeEngine[object]) -> str:
    try:
        return type(sql_type.as_generic()).__name__
    except NotImplementedError:
        return type(sql_type).__name__


def _reset_cached_database_clients() -> None:
    postgres_client._connections.clear()
    postgres_client._engines.clear()


def _set_test_database_env() -> dict[str, str | None]:
    original_values: dict[str, str | None] = {}
    for key, value in TEST_DATABASE_ENV.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    return original_values


def _restore_test_database_env(original_values: dict[str, str | None]) -> None:
    for key, previous_value in original_values.items():
        if previous_value is None:
            os.environ.pop(key, None)
            continue
        os.environ[key] = previous_value
