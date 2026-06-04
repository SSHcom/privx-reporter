"""Tests for migration down module."""

import argparse
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
@patch("administration.migration.down.module.rollback_migrations")
def test_handle_down_rejects_non_integer_steps(mock_rollback: MagicMock) -> None:
    from administration.migration.down.module import handle_down_migration

    result = handle_down_migration(argparse.Namespace(subcommand="down", steps="abc"))

    assert result == {"error_message": "--steps must be an integer.", "info_message": None}
    mock_rollback.assert_not_called()


@pytest.mark.unit
@patch("administration.migration.down.module.rollback_migrations", return_value=[])
def test_handle_down_returns_no_applied_message(mock_rollback: MagicMock) -> None:
    from administration.migration.down.module import handle_down_migration

    result = handle_down_migration(argparse.Namespace(subcommand="down", steps="1"))

    assert result == {"error_message": None, "info_message": "No applied migrations to roll back."}
    mock_rollback.assert_called_once_with(1)


@pytest.mark.unit
@patch("administration.migration.down.module.rollback_migrations", return_value=[])
def test_handle_down_defaults_to_one_when_steps_is_missing_or_none(mock_rollback: MagicMock) -> None:
    from administration.migration.down.module import handle_down_migration

    result_missing = handle_down_migration(argparse.Namespace(subcommand="down"))
    result_none = handle_down_migration(argparse.Namespace(subcommand="down", steps=None))

    assert result_missing == {"error_message": None, "info_message": "No applied migrations to roll back."}
    assert result_none == {"error_message": None, "info_message": "No applied migrations to roll back."}
    assert mock_rollback.call_count == 2
    mock_rollback.assert_any_call(1)


@pytest.mark.unit
@patch("administration.migration.down.module.rollback_migrations", return_value=["2026-04-16-x"])
def test_handle_down_prints_rolled_back_migrations(
    mock_rollback: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    from administration.migration.down.module import handle_down_migration

    result = handle_down_migration(argparse.Namespace(subcommand="down", steps="1"))

    assert result == {"error_message": None, "info_message": "Rolled back migration '2026-04-16-x'."}
    assert "Rolled back migration: 2026-04-16-x" in capsys.readouterr().out
    mock_rollback.assert_called_once_with(1)


@pytest.mark.unit
@patch(
    "administration.migration.down.module.rollback_migrations",
    return_value=["2026-04-17-create-all-tables (data)", "2026-04-17-create-all-tables (admin)"],
)
def test_handle_down_reports_single_migration_across_admin_and_data_tables(
    mock_rollback: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    from administration.migration.down.module import handle_down_migration

    result = handle_down_migration(argparse.Namespace(subcommand="down", steps="1"))

    assert result == {
        "error_message": None,
        "info_message": "Rolled back migration '2026-04-17-create-all-tables' for admin tables and data tables.",
    }
    output = capsys.readouterr().out
    assert "Rolled back migration: 2026-04-17-create-all-tables (data)" in output
    assert "Rolled back migration: 2026-04-17-create-all-tables (admin)" in output
    mock_rollback.assert_called_once_with(1)
