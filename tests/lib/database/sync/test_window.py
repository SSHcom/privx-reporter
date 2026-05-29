"""Tests for SyncWindow adaptive time-window iterator."""

from datetime import UTC, datetime

import pytest

from lib.database.sync.time_series.window import SyncWindow
from lib.env_sync import (
    DEFAULT_SYNC_MAX_RECORDS_PER_WINDOW,
    DEFAULT_SYNC_WINDOW_SIZE_DOWN_MINUTES,
    DEFAULT_SYNC_WINDOW_SIZES_MINUTES,
)


def _utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2025, 6, 1, hour, minute, tzinfo=UTC)


def _window(
    start_time: datetime,
    end_time: datetime,
    window_sizes_minutes: list[int] | None = None,
    max_records_per_window: int = DEFAULT_SYNC_MAX_RECORDS_PER_WINDOW,
    window_size_down_minutes: int = DEFAULT_SYNC_WINDOW_SIZE_DOWN_MINUTES,
) -> SyncWindow:
    return SyncWindow(
        start_time,
        end_time,
        window_sizes_minutes=window_sizes_minutes or DEFAULT_SYNC_WINDOW_SIZES_MINUTES,
        max_records_per_window=max_records_per_window,
        window_size_down_minutes=window_size_down_minutes,
    )


class TestBasicIteration:
    @pytest.mark.unit
    def test_walks_full_range(self) -> None:
        window = _window(_utc(10), _utc(10, 6), window_sizes_minutes=[3])

        starts = []
        while not window.done:
            start, end = window.next_window()
            starts.append(start)
            window.advance()

        assert starts == [_utc(10), _utc(10, 3)]

    @pytest.mark.unit
    def test_done_when_start_equals_end(self) -> None:
        window = _window(_utc(10), _utc(10))
        assert window.done is True

    @pytest.mark.unit
    def test_last_window_clamped_to_end_time(self) -> None:
        window = _window(_utc(10), _utc(10, 4), window_sizes_minutes=[3])

        window.next_window()
        window.advance()
        _, end = window.next_window()

        assert end == _utc(10, 4)

    @pytest.mark.unit
    def test_starts_at_smallest_window(self) -> None:
        window = _window(_utc(10), _utc(11), window_sizes_minutes=[3, 5, 10, 15])
        assert window.current_window_minutes == 3


class TestProactiveScaling:
    @pytest.mark.unit
    def test_grows_when_record_count_is_low(self) -> None:
        window = _window(
            _utc(10),
            _utc(11),
            window_sizes_minutes=[3, 5, 10],
            max_records_per_window=1000,
        )
        assert window.current_window_minutes == 3

        window.advance(record_count=500)
        assert window.current_window_minutes == 5

        window.advance(record_count=500)
        assert window.current_window_minutes == 10

    @pytest.mark.unit
    def test_does_not_grow_past_largest(self) -> None:
        window = _window(
            _utc(10),
            _utc(11),
            window_sizes_minutes=[3, 5],
            max_records_per_window=1000,
        )
        window.advance(record_count=100)
        assert window.current_window_minutes == 5

        window.advance(record_count=100)
        assert window.current_window_minutes == 5

    @pytest.mark.unit
    def test_shrinks_when_record_count_is_high(self) -> None:
        window = _window(
            _utc(10),
            _utc(11),
            window_sizes_minutes=[3, 5, 10],
            max_records_per_window=1000,
        )
        # Grow first
        window.advance(record_count=100)
        window.advance(record_count=100)
        assert window.current_window_minutes == 10

        # High record count triggers shrink
        window.advance(record_count=5000)
        assert window.current_window_minutes == 5

    @pytest.mark.unit
    def test_no_change_when_record_count_is_none(self) -> None:
        window = _window(
            _utc(10),
            _utc(11),
            window_sizes_minutes=[3, 5],
        )
        window.advance(record_count=None)
        assert window.current_window_minutes == 3


class TestReactiveShrink:
    @pytest.mark.unit
    def test_shrink_reduces_window(self) -> None:
        window = _window(
            _utc(10),
            _utc(11),
            window_sizes_minutes=[3, 5, 10],
        )
        # Grow to largest
        window.advance(record_count=0)
        window.advance(record_count=0)
        assert window.current_window_minutes == 10

        assert window.shrink() is True
        assert window.current_window_minutes == 5

    @pytest.mark.unit
    def test_shrink_returns_false_at_minimum(self) -> None:
        window = _window(
            _utc(10),
            _utc(11),
            window_sizes_minutes=[3, 5],
        )
        assert window.is_minimum_window is True
        assert window.shrink() is False
        assert window.current_window_minutes == 3

    @pytest.mark.unit
    def test_shrink_does_not_advance_cursor(self) -> None:
        window = _window(
            _utc(10),
            _utc(11),
            window_sizes_minutes=[3, 5],
        )
        window.advance(record_count=0)

        start_before, _ = window.next_window()
        window.shrink()
        start_after, _ = window.next_window()

        assert start_before == start_after

    @pytest.mark.unit
    def test_shrink_uses_configured_down_step_minutes(self) -> None:
        window = _window(
            _utc(10),
            _utc(11),
            window_sizes_minutes=[3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            window_size_down_minutes=5,
        )
        # Grow to largest
        for _ in range(12):
            window.advance(record_count=0)
        assert window.current_window_minutes == 15

        assert window.shrink() is True
        assert window.current_window_minutes == 10


class TestEdgeCases:
    @pytest.mark.unit
    def test_single_window_size(self) -> None:
        window = _window(_utc(10), _utc(10, 3), window_sizes_minutes=[3])

        assert window.is_minimum_window is True
        assert window.shrink() is False

        window.advance(record_count=50_000)
        assert window.current_window_minutes == 3
        assert window.done is True

    @pytest.mark.unit
    def test_window_sizes_are_sorted(self) -> None:
        window = _window(_utc(10), _utc(11), window_sizes_minutes=[10, 3, 5])
        assert window.current_window_minutes == 3

    @pytest.mark.unit
    def test_empty_window_sizes_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one entry"):
            SyncWindow(
                _utc(10),
                _utc(11),
                window_sizes_minutes=[],
                max_records_per_window=DEFAULT_SYNC_MAX_RECORDS_PER_WINDOW,
                window_size_down_minutes=DEFAULT_SYNC_WINDOW_SIZE_DOWN_MINUTES,
            )

    @pytest.mark.unit
    def test_non_positive_down_step_raises(self) -> None:
        with pytest.raises(ValueError, match="positive integer"):
            SyncWindow(
                _utc(10),
                _utc(11),
                window_sizes_minutes=DEFAULT_SYNC_WINDOW_SIZES_MINUTES,
                max_records_per_window=DEFAULT_SYNC_MAX_RECORDS_PER_WINDOW,
                window_size_down_minutes=0,
            )
