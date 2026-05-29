"""Tests for database sync helper functions."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import Column, DateTime, MetaData, Table

from lib.database.sync.time_series.helpers import (
    build_timestamped_rows,
    calculate_backfill_range,
    calculate_time_range,
    get_latest_timestamp,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("db_value", "expected"),
    [
        (datetime(2025, 1, 9, 12, 0, 0), datetime(2025, 1, 9, 12, 0, 0, tzinfo=UTC)),
        (datetime(2025, 1, 9, 12, 0, 0, tzinfo=UTC), datetime(2025, 1, 9, 12, 0, 0, tzinfo=UTC)),
        (None, None),
    ],
)
@patch("lib.database.sync.time_series.helpers.use_database")
def test_get_latest_timestamp_normalizes_results(
    mock_use_database: MagicMock, db_value: datetime | None, expected: datetime | None
) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)
    mock_db.connection.execute().scalar.return_value = db_value
    mock_use_database.return_value = mock_db

    table = Table("test_table", MetaData(), Column("timestamp", DateTime))
    assert get_latest_timestamp(table) == expected


@pytest.mark.unit
@patch("lib.database.sync.time_series.helpers.datetime")
def test_calculate_time_range_uses_latest_when_present(mock_datetime: MagicMock) -> None:
    now = datetime(2025, 1, 9, 14, 0, 0, tzinfo=UTC)
    latest = datetime(2025, 1, 9, 12, 0, 0, tzinfo=UTC)
    mock_datetime.now.return_value = now

    start, end = calculate_time_range(latest, range_minutes=60)
    assert start == latest
    assert end == now


@pytest.mark.unit
@patch("lib.database.sync.time_series.helpers.datetime")
def test_calculate_time_range_falls_back_to_minutes(mock_datetime: MagicMock) -> None:
    now = datetime(2025, 1, 9, 14, 0, 0, tzinfo=UTC)
    mock_datetime.now.return_value = now
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    start, end = calculate_time_range(None, range_minutes=120)
    assert end == now
    assert start == now - timedelta(minutes=120)


@pytest.mark.unit
@patch("lib.database.sync.time_series.helpers.datetime")
def test_calculate_time_range_clamps_latest_to_max_range(mock_datetime: MagicMock) -> None:
    now = datetime(2025, 1, 9, 14, 0, 0, tzinfo=UTC)
    too_old_latest = datetime(2025, 1, 7, 14, 0, 0, tzinfo=UTC)
    mock_datetime.now.return_value = now

    start, end = calculate_time_range(too_old_latest, range_minutes=60, max_range_hours=24)
    assert end == now
    assert start == now - timedelta(hours=24)


@pytest.mark.unit
def test_build_timestamped_rows_filters_duplicates_and_preserves_data() -> None:
    latest = datetime(2025, 1, 9, 12, 0, 0, tzinfo=UTC)
    items = [
        {"created": "2025-01-09T11:00:00Z", "id": "old"},
        {"created": "2025-01-09T12:00:00Z", "id": "equal"},
        {"created": "2025-01-09T13:00:00Z", "id": "new", "nested": {"x": 1}},
    ]

    result = build_timestamped_rows(items, latest)
    assert [row["data"]["id"] for row in result] == ["equal", "new"]
    assert result[1]["data"]["nested"]["x"] == 1


@pytest.mark.unit
def test_build_timestamped_rows_supports_custom_timestamp_key() -> None:
    latest = datetime(2025, 1, 9, 12, 0, 0, tzinfo=UTC)
    result = build_timestamped_rows(
        [{"updated": "2025-01-09T13:00:00+00:00", "id": "new"}],
        latest,
        timestamp_key="updated",
    )
    assert result[0]["data"]["id"] == "new"


@pytest.mark.unit
@patch("lib.database.sync.time_series.helpers.datetime")
def test_calculate_backfill_range_with_days(mock_datetime: MagicMock) -> None:
    now = datetime(2025, 1, 15, 14, 0, 0, tzinfo=UTC)
    mock_datetime.now.return_value = now

    start, end = calculate_backfill_range(days=7)
    assert end == now
    assert start == now - timedelta(days=7)


@pytest.mark.unit
def test_calculate_backfill_range_with_from_date() -> None:
    from_date = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    start, end = calculate_backfill_range(from_date=from_date)
    assert start == from_date
    assert end.tzinfo == UTC


@pytest.mark.unit
def test_calculate_backfill_range_raises_when_neither_provided() -> None:
    with pytest.raises(ValueError, match="Either 'days' or 'from_date' must be provided"):
        calculate_backfill_range()


@pytest.mark.unit
def test_calculate_backfill_range_raises_when_both_provided() -> None:
    from_date = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="Cannot specify both 'days' and 'from_date'"):
        calculate_backfill_range(days=7, from_date=from_date)
