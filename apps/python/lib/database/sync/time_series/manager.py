"""Shared sync loop implementation for all sync sources."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import privx_api.exceptions
from sqlalchemy.dialects.postgresql import insert as pg_insert

from lib.clients.postgresql import use_database
from lib.clients.privx.retry import RetryExhaustedError, is_retryable, with_retry
from lib.database.sync.time_series.helpers import build_timestamped_row, calculate_time_range, get_latest_timestamp
from lib.database.sync.time_series.window import SyncWindow
from lib.utils.date import format_iso_timestamp

if TYPE_CHECKING:
    from datetime import datetime

    from lib.database.sync.time_series.protocol import FetchResult, SyncSource

logger = logging.getLogger(__name__)


class SyncManager:
    """Manages sync operations for a single source implementation."""

    def __init__(self, source: SyncSource) -> None:
        self.source = source

    def sync(
        self,
        api: object,
        range_minutes: int,
        batch_size: int,
        max_range_hours: int | None = None,
        *,
        window_sizes_minutes: list[int],
        max_records_per_window: int,
        window_size_down_minutes: int,
    ) -> int:
        logger.info("---- Syncing %s... ----", self.source.name)
        latest_timestamp = get_latest_timestamp(self.source.table)

        start_time, end_time = calculate_time_range(
            latest_timestamp,
            range_minutes,
            max_range_hours=max_range_hours,
        )

        context = self.source.prepare(api)

        return self._run_sync_loop(
            api=api,
            start_time=start_time,
            end_time=end_time,
            batch_size=batch_size,
            latest_timestamp=latest_timestamp,
            context=context,
            window_sizes_minutes=window_sizes_minutes,
            max_records_per_window=max_records_per_window,
            window_size_down_minutes=window_size_down_minutes,
        )

    def backfill(
        self,
        api: object,
        start_time: datetime,
        end_time: datetime,
        batch_size: int,
        *,
        window_sizes_minutes: list[int],
        max_records_per_window: int,
        window_size_down_minutes: int,
    ) -> int:
        logger.info("---- Backfilling %s... ----", self.source.name)
        logger.info("Range: %s to %s", start_time, end_time)
        context = self.source.prepare(api)

        return self._run_sync_loop(
            api=api,
            start_time=start_time,
            end_time=end_time,
            batch_size=batch_size,
            latest_timestamp=None,
            context=context,
            window_sizes_minutes=window_sizes_minutes,
            max_records_per_window=max_records_per_window,
            window_size_down_minutes=window_size_down_minutes,
        )

    def _fetch_with_retry(
        self,
        api: object,
        start_time_str: str,
        end_time_str: str,
        offset: int,
        batch_size: int,
    ) -> FetchResult | None:
        try:
            return with_retry(
                lambda: self.source.fetch_batch(
                    api=api,
                    start_time=start_time_str,
                    end_time=end_time_str,
                    offset=offset,
                    limit=batch_size,
                ),
                operation=f"fetch {self.source.name}",
            )
        except RetryExhaustedError as error:
            logger.error(
                "Sync failed for %s after %s retries: %s",
                self.source.name,
                error.attempts,
                error.last_error,
            )
            return None
        except privx_api.exceptions.InternalAPIException as error:
            logger.error("API error during %s sync: %s", self.source.name, error)
            return None

    def _run_sync_loop(
        self,
        api: object,
        start_time: datetime,
        end_time: datetime,
        batch_size: int,
        latest_timestamp: datetime | None,
        context: object,
        window_sizes_minutes: list[int],
        max_records_per_window: int,
        window_size_down_minutes: int,
    ) -> int:
        window = SyncWindow(
            start_time,
            end_time,
            window_sizes_minutes=window_sizes_minutes,
            max_records_per_window=max_records_per_window,
            window_size_down_minutes=window_size_down_minutes,
        )
        total_inserted = 0

        while not window.done:
            win_start, win_end = window.next_window()
            start_str = format_iso_timestamp(win_start)
            end_str = format_iso_timestamp(win_end)

            logger.info(
                "Syncing %s window %s -> %s (%s min)",
                self.source.name,
                start_str,
                end_str,
                window.current_window_minutes,
            )

            try:
                outcome = self._fetch_window(
                    api=api,
                    start_time_str=start_str,
                    end_time_str=end_str,
                    batch_size=batch_size,
                    latest_timestamp=latest_timestamp,
                    context=context,
                    use_retry=window.is_minimum_window,
                )
            except Exception as error:
                if is_retryable(error) and window.shrink():
                    continue
                logger.error("Unrecoverable error during %s sync: %s", self.source.name, error)
                break

            if outcome is None:
                break

            inserted, total_count = outcome
            total_inserted += inserted
            window.advance(record_count=total_count)

        logger.info("Total inserted %s: %s", self.source.name, total_inserted)
        return total_inserted

    def _fetch_window(
        self,
        api: object,
        start_time_str: str,
        end_time_str: str,
        batch_size: int,
        latest_timestamp: datetime | None,
        context: object,
        *,
        use_retry: bool,
    ) -> tuple[int, int | None] | None:
        """Paginate through a single time window.

        Returns ``(rows_inserted, total_count)`` on success, or ``None``
        when the sync should be aborted (retry exhaustion at minimum window).
        """
        offset = 0
        window_inserted = 0
        total_count: int | None = None

        while True:
            logger.debug(
                "Fetching %s batch %s -> %s (offset=%s)",
                self.source.name,
                start_time_str,
                end_time_str,
                offset,
            )

            if use_retry:
                result = self._fetch_with_retry(
                    api=api,
                    start_time_str=start_time_str,
                    end_time_str=end_time_str,
                    offset=offset,
                    batch_size=batch_size,
                )
                if result is None:
                    logger.warning("Aborting %s sync cycle due to API errors", self.source.name)
                    return None
            else:
                result = self.source.fetch_batch(
                    api=api,
                    start_time=start_time_str,
                    end_time=end_time_str,
                    offset=offset,
                    limit=batch_size,
                )

            if result.count == 0:
                break

            if offset == 0 and result.total_count is not None:
                total_count = result.total_count

            logger.debug("Offset: %s, %s in batch: %s", offset, self.source.name, result.count)
            offset += batch_size

            rows = self._process_batch(result.items, latest_timestamp, context)

            if not rows:
                if result.count < batch_size:
                    break
                continue

            self._insert_rows(rows)
            window_inserted += len(rows)

            if result.count < batch_size:
                break

        return window_inserted, total_count

    def _process_batch(
        self,
        items: list[dict[str, Any]],
        latest_timestamp: datetime | None,
        context: object,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        passed_filter = 0
        filtered_out = 0

        for item in items:
            if not self.source.filter_item(item, context):
                filtered_out += 1
                continue

            passed_filter += 1
            self.source.normalize_item(item)
            row = build_timestamped_row(item, latest_timestamp, self.source.timestamp_key)

            if row is None:
                continue

            record_id = self.source.build_record_id(row["data"])

            if record_id is None:
                logger.error("Skipping %s record due to missing required ID fields", self.source.name)
                continue

            row["record_id"] = record_id
            row.update(self.source.build_row_extras(row["data"]))
            rows.append(row)

        logger.debug(
            "%s batch filter results: total=%s passed_filter=%s filtered_out=%s rows_ready=%s",
            self.source.name,
            len(items),
            passed_filter,
            filtered_out,
            len(rows),
        )
        return rows

    def _insert_rows(self, rows: list[dict[str, Any]]) -> None:
        db = use_database("data")

        with db.connection.begin():
            db.connection.execute(
                pg_insert(self.source.table).on_conflict_do_nothing(),
                rows,
            )

        logger.info("Inserted %s new %s", len(rows), self.source.name)
