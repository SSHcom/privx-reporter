from __future__ import annotations

import time
from copy import deepcopy
from datetime import datetime, timedelta
from time import perf_counter
from typing import TYPE_CHECKING, Any, Protocol
from unittest.mock import patch

from lib.clients.postgresql import use_database
from lib.database.sync import sync_connections
from live_test._shared.common import (
    CONNECTION_SAMPLE_PATH,
    TEST_RUN_ID_FIELD,
    RunMetrics,
    base_test_time,
    load_sample,
    to_iso_z,
)

if TYPE_CHECKING:
    from lib.env_sync import SyncConfig, SyncSourceConfig


class ConnectionFetcher(Protocol):
    def __call__(
        self,
        api: object,
        offset: int = 0,
        limit: int | None = None,
        sort_key: str | None = None,
        sort_dir: str | None = None,
        search_payload: dict[str, Any] | None = None,
        propagate_errors: bool = False,
    ) -> dict[str, Any]: ...


def _build_record(sample: dict[str, Any], run_id: str, start_at: datetime, index: int) -> dict[str, Any]:
    base_id = str(sample.get("id", "connection"))
    record = deepcopy(sample)
    connected = start_at + timedelta(milliseconds=index)
    disconnected = connected + timedelta(seconds=30)

    record["id"] = f"{base_id}-{index}"
    record["connected"] = to_iso_z(connected)
    record["disconnected"] = to_iso_z(disconnected)
    record["created"] = to_iso_z(connected)
    record["updated"] = to_iso_z(disconnected)
    record["last_activity"] = to_iso_z(connected + timedelta(seconds=3))
    record["duration"] = 30
    record[TEST_RUN_ID_FIELD] = run_id
    return record


def _build_fake_api(
    sample: dict[str, Any],
    record_count: int,
    run_id: str,
    api_delay_ms: int,
    metrics: RunMetrics,
) -> ConnectionFetcher:
    start_at = base_test_time()

    def _fake_search_connections(
        api: object,
        offset: int = 0,
        limit: int | None = None,
        sort_key: str | None = None,
        sort_dir: str | None = None,
        search_payload: dict[str, Any] | None = None,
        propagate_errors: bool = False,
    ) -> dict[str, Any]:
        del api, sort_key, sort_dir, search_payload, propagate_errors
        if api_delay_ms > 0:
            sleep_seconds = api_delay_ms / 1000
            time.sleep(sleep_seconds)
            metrics.api_wait_seconds += sleep_seconds
        page_size = record_count if limit is None else limit
        if offset >= record_count:
            return {"count": record_count, "items": []}

        end_offset = min(offset + page_size, record_count)
        started = perf_counter()
        items = [_build_record(sample, run_id, start_at, index) for index in range(offset, end_offset)]
        metrics.generation_seconds += perf_counter() - started
        return {"count": record_count, "items": items}

    return _fake_search_connections


def run(
    config: SyncConfig,
    source_config: SyncSourceConfig,
    record_count: int,
    api_delay_ms: int,
    run_id: str,
) -> RunMetrics:
    sample = load_sample(CONNECTION_SAMPLE_PATH)
    metrics = RunMetrics()
    fake_api = _build_fake_api(sample, record_count, run_id, api_delay_ms, metrics)
    db = use_database("data")
    original_execute = db.connection.execute

    def _timed_execute(*args: object, **kwargs: object) -> object:
        started = perf_counter()
        result = original_execute(*args, **kwargs)
        metrics.db_seconds += perf_counter() - started
        return result

    with (
        patch("lib.database.sync.time_series.sources.connection.report_api.search_connections", side_effect=fake_api),
        patch("lib.database.sync.time_series.manager.get_latest_timestamp", return_value=None),
        patch.object(db.connection, "execute", side_effect=_timed_execute),
    ):
        sync_connections(
            api=object(),
            range_minutes=source_config.range_minutes,
            batch_size=config.batch_size,
            max_range_hours=config.max_range_hours,
            window_sizes_minutes=config.window_sizes_minutes,
            max_records_per_window=config.max_records_per_window,
            window_size_down_minutes=config.window_size_down_minutes,
        )

    return metrics
