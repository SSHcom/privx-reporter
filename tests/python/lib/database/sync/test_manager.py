"""Tests for shared sync manager."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import privx_api.exceptions
import pytest

from lib.clients.privx.retry import RetryExhausted
from lib.database.sync.time_series.manager import SyncManager
from lib.database.sync.time_series.protocol import FetchResult
from lib.env_sync import (
    DEFAULT_SYNC_MAX_RECORDS_PER_WINDOW,
    DEFAULT_SYNC_WINDOW_SIZE_DOWN_MINUTES,
    DEFAULT_SYNC_WINDOW_SIZES_MINUTES,
)


def _source() -> MagicMock:
    source = MagicMock()
    source.name = "connections"
    source.table = MagicMock()
    source.timestamp_key = "connected"
    source.prepare.return_value = None
    source.filter_item.return_value = True
    source.build_record_id.return_value = "conn-1|2026-01-01T00:00:00Z"
    source.build_row_extras.return_value = {}
    return source


_T0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
_ITEM = {"id": "conn-1", "connected": "2026-01-01T00:00:00Z"}


def _sync(manager: SyncManager, mock_api: MagicMock, *, range_minutes: int, batch_size: int) -> int:
    return manager.sync(
        mock_api,
        range_minutes=range_minutes,
        batch_size=batch_size,
        window_sizes_minutes=DEFAULT_SYNC_WINDOW_SIZES_MINUTES,
        max_records_per_window=DEFAULT_SYNC_MAX_RECORDS_PER_WINDOW,
        window_size_down_minutes=DEFAULT_SYNC_WINDOW_SIZE_DOWN_MINUTES,
    )


@pytest.mark.unit
@patch("lib.database.sync.time_series.manager.SyncManager._insert_rows")
@patch("lib.database.sync.time_series.manager.build_timestamped_row")
@patch("lib.database.sync.time_series.manager.calculate_time_range")
@patch("lib.database.sync.time_series.manager.get_latest_timestamp")
def test_sync_inserts_rows_from_single_window(
    mock_latest: MagicMock,
    mock_range: MagicMock,
    mock_build_row: MagicMock,
    mock_insert_rows: MagicMock,
    mock_api: MagicMock,
) -> None:
    """A 3-minute range fits in the initial window — one fetch, one insert."""
    source = _source()
    manager = SyncManager(source)
    start_time = _T0
    end_time = _T0 + timedelta(minutes=3)

    mock_latest.return_value = _T0
    mock_range.return_value = (start_time, end_time)
    source.fetch_batch.side_effect = [
        FetchResult(items=[_ITEM], count=1, total_count=1),
    ]
    mock_build_row.return_value = {"timestamp": start_time, "data": _ITEM}

    inserted = _sync(manager, mock_api, range_minutes=3, batch_size=100)

    assert inserted == 1
    source.fetch_batch.assert_called_once()
    mock_insert_rows.assert_called_once()


@pytest.mark.unit
@patch("lib.database.sync.time_series.manager.SyncManager._insert_rows")
@patch("lib.database.sync.time_series.manager.build_timestamped_row")
@patch("lib.database.sync.time_series.manager.calculate_time_range")
@patch("lib.database.sync.time_series.manager.get_latest_timestamp")
def test_sync_walks_multiple_windows(
    mock_latest: MagicMock,
    mock_range: MagicMock,
    mock_build_row: MagicMock,
    mock_insert_rows: MagicMock,
    mock_api: MagicMock,
) -> None:
    """A range longer than one window produces multiple fetch_batch calls."""
    source = _source()
    manager = SyncManager(source)
    start_time = _T0
    end_time = _T0 + timedelta(minutes=6)

    mock_latest.return_value = _T0
    mock_range.return_value = (start_time, end_time)
    source.fetch_batch.side_effect = [
        FetchResult(items=[_ITEM], count=1, total_count=1),
        FetchResult(items=[_ITEM], count=1, total_count=1),
    ]
    mock_build_row.return_value = {"timestamp": start_time, "data": _ITEM}

    inserted = _sync(manager, mock_api, range_minutes=6, batch_size=100)

    assert inserted == 2
    assert source.fetch_batch.call_count == 2


@pytest.mark.unit
@patch("lib.database.sync.time_series.manager.SyncManager._insert_rows")
@patch("lib.database.sync.time_series.manager.build_timestamped_row")
@patch("lib.database.sync.time_series.manager.calculate_time_range")
@patch("lib.database.sync.time_series.manager.get_latest_timestamp")
def test_sync_shrinks_window_on_retryable_error(
    mock_latest: MagicMock,
    mock_range: MagicMock,
    mock_build_row: MagicMock,
    mock_insert_rows: MagicMock,
    mock_api: MagicMock,
) -> None:
    """A retryable error at a non-minimum window shrinks and retries the same position."""
    source = _source()
    manager = SyncManager(source)
    start_time = _T0
    end_time = _T0 + timedelta(minutes=5)

    mock_latest.return_value = _T0
    mock_range.return_value = (start_time, end_time)

    # First window (3 min) succeeds with low count → window grows to 5 min.
    # Second window (5 min) raises retryable 504 → shrinks back to 3 min.
    # Retry at 3 min succeeds.
    source.fetch_batch.side_effect = [
        FetchResult(items=[_ITEM], count=1, total_count=1),
        privx_api.exceptions.InternalAPIException("timeout", 504),
        FetchResult(items=[_ITEM], count=1, total_count=1),
    ]
    mock_build_row.return_value = {"timestamp": start_time, "data": _ITEM}

    inserted = _sync(manager, mock_api, range_minutes=5, batch_size=100)

    assert inserted == 2
    assert source.fetch_batch.call_count == 3


@pytest.mark.unit
@patch("lib.database.sync.time_series.manager.SyncManager._insert_rows")
@patch("lib.database.sync.time_series.manager.build_timestamped_row")
@patch("lib.database.sync.time_series.manager.calculate_time_range")
@patch("lib.database.sync.time_series.manager.get_latest_timestamp")
def test_sync_aborts_on_retry_exhaustion_at_minimum_window(
    mock_latest: MagicMock,
    mock_range: MagicMock,
    mock_build_row: MagicMock,
    mock_insert_rows: MagicMock,
    mock_api: MagicMock,
) -> None:
    """At minimum window, retry exhaustion aborts the sync gracefully."""
    source = _source()
    manager = SyncManager(source)
    start_time = _T0
    end_time = _T0 + timedelta(minutes=3)

    mock_latest.return_value = _T0
    mock_range.return_value = (start_time, end_time)
    error = privx_api.exceptions.InternalAPIException("timeout", 504)
    source.fetch_batch.side_effect = error

    with patch("lib.database.sync.time_series.manager.with_retry", side_effect=RetryExhausted(error, 5)):
        inserted = _sync(manager, mock_api, range_minutes=3, batch_size=100)

    assert inserted == 0
    mock_insert_rows.assert_not_called()


@pytest.mark.unit
@patch("lib.database.sync.time_series.manager.logger")
def test_fetch_with_retry_returns_none_on_retry_exhaustion(mock_logger: MagicMock, mock_api: MagicMock) -> None:
    source = _source()
    manager = SyncManager(source)
    exhausted = RetryExhausted(last_error=RuntimeError("api down"), attempts=5)

    with patch("lib.database.sync.time_series.manager.with_retry", side_effect=exhausted):
        result = manager._fetch_with_retry(  # pylint: disable=protected-access
            api=mock_api,
            start_time_str="2026-01-01T00:00:00Z",
            end_time_str="2026-01-01T01:00:00Z",
            offset=0,
            batch_size=100,
        )

    assert result is None
    mock_logger.error.assert_called_once()
