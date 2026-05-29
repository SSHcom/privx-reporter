"""Tests for migration up module."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
@patch("administration.migration.up.module.apply_pending_migrations", return_value=[])
def test_handle_up_returns_no_pending_message(mock_apply: MagicMock) -> None:
    from administration.migration.up.module import handle_up_migration

    result = handle_up_migration()

    assert result == {"error_message": None, "info_message": "No pending migrations."}
    mock_apply.assert_called_once()


@pytest.mark.unit
@patch("administration.migration.up.module.apply_pending_migrations")
def test_handle_up_prints_applied_migrations(mock_apply: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    from administration.migration._shared.runner import MigrationFile
    from administration.migration.up.module import handle_up_migration

    mock_apply.return_value = [MigrationFile("2026-04-16-x", "admin", ["SELECT 1"], ["SELECT 2"])]
    result = handle_up_migration()

    assert result == {"error_message": None, "info_message": "Applied migration '2026-04-16-x' for admin tables."}
    assert "Applied migration: 2026-04-16-x (admin)" in capsys.readouterr().out


@pytest.mark.unit
@patch("administration.migration.up.module.apply_pending_migrations")
def test_handle_up_reports_single_migration_across_admin_and_data_tables(
    mock_apply: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    from administration.migration._shared.runner import MigrationFile
    from administration.migration.up.module import handle_up_migration

    mock_apply.return_value = [
        MigrationFile("2026-04-17-create-all-tables", "admin", ["SELECT 1"], ["SELECT 2"]),
        MigrationFile("2026-04-17-create-all-tables", "data", ["SELECT 3"], ["SELECT 4"]),
    ]
    result = handle_up_migration()

    assert result == {
        "error_message": None,
        "info_message": "Applied migration '2026-04-17-create-all-tables' for admin tables and data tables.",
    }
    output = capsys.readouterr().out
    assert "Applied migration: 2026-04-17-create-all-tables (admin)" in output
    assert "Applied migration: 2026-04-17-create-all-tables (data)" in output
