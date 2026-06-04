"""Tests for migration runner behavior."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from administration.migration._shared.runner import (
    AppliedMigration,
    MigrationFile,
    MigrationStatus,
    apply_pending_migrations,
    discover_migrations,
    get_migration_status,
    rollback_migrations,
)


def _write_migration_file(path: Path, target_db: str, up_sql: str, down_sql: str) -> None:
    path.write_text(
        "\n".join(
            [
                'ADMIN_DB = "admin"',
                'DATA_DB = "data"',
                "",
                "def up() -> dict[str, list[str]]:",
                f'    return {{"{target_db}": ["{up_sql}"]}}',
                "",
                "def down() -> dict[str, list[str]]:",
                f'    return {{"{target_db}": ["{down_sql}"]}}',
                "",
            ]
        ),
        encoding="utf-8",
    )


@pytest.mark.unit
def test_discover_migrations_orders_by_filename(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    first = tmp_path / "2026-04-16-add-a.py"
    second = tmp_path / "2026-04-17-add-b.py"
    ignored = tmp_path / "invalid_name.py"
    _write_migration_file(first, "admin", "SELECT 1", "SELECT 2")
    _write_migration_file(second, "data", "SELECT 3", "SELECT 4")
    _write_migration_file(ignored, "admin", "SELECT 5", "SELECT 6")

    monkeypatch.setattr("administration.migration._shared.runner.MIGRATIONS_DIR", tmp_path)
    migrations = discover_migrations()

    assert [migration.name for migration in migrations] == ["2026-04-16-add-a", "2026-04-17-add-b"]
    assert migrations[0].target_db == "admin"
    assert migrations[1].target_db == "data"


@pytest.mark.unit
def test_discover_migrations_expands_single_file_to_both_databases(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    migration_file = tmp_path / "2026-04-16-multi-db.py"
    migration_file.write_text(
        "\n".join(
            [
                'ADMIN_DB = "admin"',
                'DATA_DB = "data"',
                "",
                "def up() -> dict[str, list[str]]:",
                '    return {"admin": ["SELECT 1"], "data": ["SELECT 2"]}',
                "",
                "def down() -> dict[str, list[str]]:",
                '    return {"admin": ["SELECT 3"], "data": ["SELECT 4"]}',
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("administration.migration._shared.runner.MIGRATIONS_DIR", tmp_path)
    migrations = discover_migrations()

    assert [(migration.name, migration.target_db) for migration in migrations] == [
        ("2026-04-16-multi-db", "admin"),
        ("2026-04-16-multi-db", "data"),
    ]


@pytest.mark.unit
def test_discover_migrations_rejects_invalid_target_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    migration_file = tmp_path / "2026-04-16-invalid-target.py"
    _write_migration_file(migration_file, "other", "SELECT 1", "SELECT 2")

    monkeypatch.setattr("administration.migration._shared.runner.MIGRATIONS_DIR", tmp_path)
    with pytest.raises(ValueError, match="invalid database key"):
        discover_migrations()


@pytest.mark.unit
@patch("administration.migration._shared.runner._record_applied_migration")
@patch("administration.migration._shared.runner.db_execute")
@patch("administration.migration._shared.runner._get_applied_migrations")
@patch("administration.migration._shared.runner.discover_migrations")
@patch("administration.migration._shared.runner.ensure_migration_history_table")
def test_apply_pending_migrations_applies_only_new_files(
    _mock_ensure: MagicMock,
    mock_discover: MagicMock,
    mock_applied: MagicMock,
    mock_db_execute: MagicMock,
    mock_record: MagicMock,
) -> None:
    migration_a = MigrationFile("2026-04-16-a", "admin", ["SELECT 1"], ["SELECT 2"])
    migration_b = MigrationFile("2026-04-17-b", "data", ["SELECT 3"], ["SELECT 4"])
    mock_discover.return_value = [migration_a, migration_b]
    mock_applied.return_value = [AppliedMigration("2026-04-16-a", "admin", datetime.now(UTC))]

    result = apply_pending_migrations()

    assert result == [migration_b]
    mock_db_execute.assert_called_once_with(["SELECT 3"], name="data")
    mock_record.assert_called_once_with(migration_b)


@pytest.mark.unit
@patch("administration.migration._shared.runner._remove_applied_migration")
@patch("administration.migration._shared.runner.db_execute")
@patch("administration.migration._shared.runner._get_applied_migrations")
@patch("administration.migration._shared.runner.discover_migrations")
@patch("administration.migration._shared.runner.ensure_migration_history_table")
def test_rollback_migrations_rolls_back_latest_first(
    _mock_ensure: MagicMock,
    mock_discover: MagicMock,
    mock_applied: MagicMock,
    mock_db_execute: MagicMock,
    mock_remove: MagicMock,
) -> None:
    migration_a = MigrationFile("2026-04-16-a", "admin", ["SELECT 1"], ["SELECT 2"])
    migration_b = MigrationFile("2026-04-17-b", "data", ["SELECT 3"], ["SELECT 4"])
    mock_discover.return_value = [migration_a, migration_b]
    mock_applied.return_value = [
        AppliedMigration("2026-04-16-a", "admin", datetime(2026, 4, 16, tzinfo=UTC)),
        AppliedMigration("2026-04-17-b", "data", datetime(2026, 4, 17, tzinfo=UTC)),
    ]

    result = rollback_migrations(steps=1)

    assert result == ["2026-04-17-b (data)"]
    mock_db_execute.assert_called_once_with(["SELECT 4"], name="data")
    mock_remove.assert_called_once_with("2026-04-17-b", "data")


@pytest.mark.unit
@patch("administration.migration._shared.runner._remove_applied_migration")
@patch("administration.migration._shared.runner.db_execute")
@patch("administration.migration._shared.runner._get_applied_migrations")
@patch("administration.migration._shared.runner.discover_migrations")
@patch("administration.migration._shared.runner.ensure_migration_history_table")
def test_rollback_migrations_rolls_back_all_targets_for_latest_migration_file(
    _mock_ensure: MagicMock,
    mock_discover: MagicMock,
    mock_applied: MagicMock,
    mock_db_execute: MagicMock,
    mock_remove: MagicMock,
) -> None:
    old_migration = MigrationFile("2026-04-16-a", "admin", ["SELECT 1"], ["SELECT 2"])
    latest_admin = MigrationFile("2026-04-17-b", "admin", ["SELECT 3"], ["SELECT 4"])
    latest_data = MigrationFile("2026-04-17-b", "data", ["SELECT 5"], ["SELECT 6"])
    mock_discover.return_value = [old_migration, latest_admin, latest_data]
    mock_applied.return_value = [
        AppliedMigration("2026-04-16-a", "admin", datetime(2026, 4, 16, tzinfo=UTC)),
        AppliedMigration("2026-04-17-b", "admin", datetime(2026, 4, 17, 10, tzinfo=UTC)),
        AppliedMigration("2026-04-17-b", "data", datetime(2026, 4, 17, 11, tzinfo=UTC)),
    ]

    result = rollback_migrations(steps=1)

    assert result == ["2026-04-17-b (data)", "2026-04-17-b (admin)"]
    assert mock_db_execute.call_args_list == [
        ((["SELECT 6"],), {"name": "data"}),
        ((["SELECT 4"],), {"name": "admin"}),
    ]
    assert mock_remove.call_args_list == [
        (("2026-04-17-b", "data"), {}),
        (("2026-04-17-b", "admin"), {}),
    ]


@pytest.mark.unit
@patch("administration.migration._shared.runner._get_applied_migrations")
@patch("administration.migration._shared.runner.discover_migrations")
@patch("administration.migration._shared.runner.ensure_migration_history_table")
def test_get_migration_status_splits_applied_and_pending(
    _mock_ensure: MagicMock,
    mock_discover: MagicMock,
    mock_applied: MagicMock,
) -> None:
    migration_a = MigrationFile("2026-04-16-a", "admin", ["SELECT 1"], ["SELECT 2"])
    migration_b = MigrationFile("2026-04-17-b", "data", ["SELECT 3"], ["SELECT 4"])
    mock_discover.return_value = [migration_a, migration_b]
    applied_row = AppliedMigration("2026-04-16-a", "admin", datetime.now(UTC))
    mock_applied.return_value = [applied_row]

    status = get_migration_status()

    assert isinstance(status, MigrationStatus)
    assert status.applied == [applied_row]
    assert status.pending == [migration_b]
