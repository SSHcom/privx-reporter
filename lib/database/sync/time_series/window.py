"""Adaptive time-window iterator for sync operations."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SyncWindow:
    """Walk a time range in adaptively-sized sub-windows.

    Starts at the smallest window and grows when record counts are low,
    shrinks when they are high or when the caller signals a failure.
    """

    def __init__(
        self,
        start_time: datetime,
        end_time: datetime,
        window_sizes_minutes: list[int],
        max_records_per_window: int,
        window_size_down_minutes: int,
    ) -> None:
        if len(window_sizes_minutes) == 0:
            raise ValueError("window_sizes_minutes must have at least one entry")
        if max_records_per_window <= 0:
            raise ValueError("max_records_per_window must be a positive integer")
        if window_size_down_minutes <= 0:
            raise ValueError("window_size_down_minutes must be a positive integer")

        self._sizes = sorted(window_sizes_minutes)
        self._max_records = max_records_per_window
        self._down_step_minutes = window_size_down_minutes
        self._start_time = start_time
        self._end_time = end_time
        self._cursor = start_time
        self._size_idx = 0

    @property
    def done(self) -> bool:
        return self._cursor >= self._end_time

    @property
    def is_minimum_window(self) -> bool:
        return self._size_idx == 0

    @property
    def current_window_minutes(self) -> int:
        return self._sizes[self._size_idx]

    def next_window(self) -> tuple[datetime, datetime]:
        """Return ``(start, end)`` for the current sub-window."""
        # timedelta(minutes=X) represents a duration of X minutes.
        # Adding duration to the cursor gives a candidate end time "X minutes later".
        window_end = min(
            self._cursor + timedelta(minutes=self.current_window_minutes),
            self._end_time,
        )
        return self._cursor, window_end

    def advance(self, record_count: int | None = None) -> None:
        """Mark the current window successful and move the cursor forward.

        Adjusts the window size for the *next* iteration based on
        ``record_count`` (proactive scaling).
        """
        _, window_end = self.next_window()
        # Move the cursor to the end of the window we just processed.
        # This makes the next window start exactly at that point, so windows
        # move forward in contiguous chunks without overlap.
        self._cursor = window_end

        if record_count is None:
            return

        if record_count > self._max_records and self._size_idx > 0:
            self._decrease_window_size()
            logger.info(
                "Window returned %s records (>%s), shrinking to %s min",
                record_count,
                self._max_records,
                self.current_window_minutes,
            )
        elif record_count <= self._max_records and self._size_idx < len(self._sizes) - 1:
            self._size_idx += 1
            logger.info(
                "Window returned %s records (<=%s), growing to %s min",
                record_count,
                self._max_records,
                self.current_window_minutes,
            )

    def _decrease_window_size(self) -> None:
        """Decrease by configured down-step minutes, mapped onto configured sizes."""
        target_minutes = self.current_window_minutes - self._down_step_minutes
        # Clamp to index 0 so we never go below the initial minimum window.
        new_idx = 0
        for idx in range(self._size_idx - 1, -1, -1):
            if self._sizes[idx] <= target_minutes:
                new_idx = idx
                break
        self._size_idx = new_idx

    def shrink(self) -> bool:
        """Reduce window size after a retryable failure.

        Returns True if the window was shrunk, False if already at minimum.
        """
        if self._size_idx > 0:
            self._decrease_window_size()
            logger.warning(
                "Retryable error, shrinking window to %s min",
                self.current_window_minutes,
            )
            return True
        return False
