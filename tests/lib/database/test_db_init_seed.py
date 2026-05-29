"""Tests for audit event sync seed logic."""

import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lib.database.db_init import _seed_audit_event_sync_table


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["CODE", "NAME", "SEVERITY", "ORIGIN"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


@pytest.mark.unit
@patch("lib.database.db_init._read_enabled_event_codes", return_value={1001})
def test_seed_inserts_rows_when_table_empty(
    _mock_enabled_codes: MagicMock,
    tmp_path: Path,
) -> None:
    all_events_csv = tmp_path / "events_all.csv"
    enabled_events_csv = tmp_path / "events_enabled.csv"
    _write_csv(
        all_events_csv,
        [
            {"CODE": "1001", "NAME": "Login", "SEVERITY": "Info", "ORIGIN": "Authentication"},
            {"CODE": "2002", "NAME": "Logout", "SEVERITY": "Info", "ORIGIN": "Authentication"},
        ],
    )
    enabled_events_csv.write_text("CODE\n1001\n", encoding="utf-8")

    mock_db = MagicMock()
    mock_db.connection.begin.return_value.__enter__.return_value = MagicMock()
    mock_db.connection.execute.return_value.scalar_one.return_value = 0

    with (
        patch("lib.database.db_init.use_database", return_value=mock_db),
        patch(
            "lib.database.db_init._get_csv_paths",
            return_value=(all_events_csv, enabled_events_csv),
        ),
    ):
        _seed_audit_event_sync_table()

    assert mock_db.connection.execute.call_count == 2
    inserted_rows = mock_db.connection.execute.call_args_list[1][0][1]
    assert inserted_rows[0]["code"] == 1001
    assert inserted_rows[0]["enabled"] is True
    assert inserted_rows[1]["enabled"] is False


@pytest.mark.unit
def test_seed_skips_insert_when_table_has_rows() -> None:
    mock_db = MagicMock()
    mock_db.connection.begin.return_value.__enter__.return_value = MagicMock()
    mock_db.connection.execute.return_value.scalar_one.return_value = 5

    with (
        patch("lib.database.db_init.use_database", return_value=mock_db),
        patch(
            "lib.database.db_init._get_csv_paths",
            return_value=(Path("/tmp/all.csv"), Path("/tmp/enabled.csv")),
        ),
        patch("lib.database.db_init._read_enabled_event_codes", return_value=set()),
    ):
        _seed_audit_event_sync_table()

    # Only count query should execute.
    assert mock_db.connection.execute.call_count == 1
