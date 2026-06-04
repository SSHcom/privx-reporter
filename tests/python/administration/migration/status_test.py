"""Tests for migration status module."""

import argparse
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
@patch("administration.migration.status.module.get_migration_status")
def test_handle_status_prints_applied_and_pending(mock_status: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    from administration.migration._shared.runner import AppliedMigration, MigrationFile, MigrationStatus
    from administration.migration.status.module import handle_status_migration

    mock_status.return_value = MigrationStatus(
        applied=[AppliedMigration("2026-04-16-a", "admin", datetime(2026, 4, 16, tzinfo=UTC))],
        pending=[MigrationFile("2026-04-17-b", "data", ["SELECT 1"], ["SELECT 2"])],
    )

    result = handle_status_migration(argparse.Namespace(subcommand="status"), {})

    assert result == {"error_message": None, "info_message": "Applied: 1. Pending: 1."}
    output = capsys.readouterr().out
    assert "Applied migrations:" in output
    assert "2026-04-16-a (admin)" in output
    assert "Pending migrations:" in output
    assert "2026-04-17-b (data)" in output
