from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import text

from lib.clients.postgresql import use_database
from lib.database.sync import sync_audit_events, sync_connections
from lib.env_sync import SyncConfig
from live_test._shared.common import (
    AUDIT_SAMPLE_PATH,
    CONNECTION_SAMPLE_PATH,
    TEST_RUN_ID_FIELD,
    base_test_time,
    cleanup_run_data,
    init_data_tables,
    load_sample,
    resolve_source_config,
    to_iso_z,
)


@dataclass
class IntegrityStats:
    total_rows: int
    duplicate_record_ids: int


@dataclass
class Scenario:
    unique_records: int
    duplicate_records: int
    batch_size: int


AUDIT_SCENARIO = Scenario(unique_records=43, duplicate_records=13, batch_size=17)
CONNECTION_SCENARIO = Scenario(unique_records=47, duplicate_records=19, batch_size=16)


def _fetch_integrity_stats(source: str, run_id: str) -> IntegrityStats:
    db = use_database("data")
    table_name = "audit_event" if source == "audit" else "connection"
    query = text(
        f"""
        SELECT
            COUNT(*)::int AS total_rows,
            COALESCE(SUM(CASE WHEN group_count > 1 THEN 1 ELSE 0 END), 0)::int AS duplicate_record_ids
        FROM (
            SELECT record_id, COUNT(*)::int AS group_count
            FROM {table_name}
            WHERE data->>'live_test_run_id' = :run_id
            GROUP BY record_id
        ) grouped
        """
    )
    with db.connection.begin():
        row = db.connection.execute(query, {"run_id": run_id}).fetchone()
    if row is None:
        return IntegrityStats(total_rows=0, duplicate_record_ids=0)
    return IntegrityStats(
        total_rows=int(row.total_rows),
        duplicate_record_ids=int(row.duplicate_record_ids),
    )


def _assert_integrity(
    source: str,
    source_records: int,
    expected_inserted_records: int,
    stats: IntegrityStats,
) -> None:
    source_label = "AUDIT" if source == "audit" else "CONNECTION"

    if stats.total_rows != expected_inserted_records:
        raise AssertionError(
            f"{source_label} integrity failed: expected {expected_inserted_records} "
            f"inserted rows, got {stats.total_rows}"
        )
    if stats.duplicate_record_ids != 0:
        raise AssertionError(
            f"{source_label} integrity failed: found {stats.duplicate_record_ids} duplicate record_id groups"
        )
    if stats.total_rows >= source_records:
        raise AssertionError(
            f"{source_label} integrity failed: duplicate source records were not filtered "
            f"(inserted {stats.total_rows} from {source_records} source records)"
        )


def _build_audit_unique_records(run_id: str, unique_records: int) -> list[dict[str, object]]:
    sample = load_sample(AUDIT_SAMPLE_PATH)
    start_at = base_test_time()
    records: list[dict[str, object]] = []

    for index in range(unique_records):
        created = start_at + timedelta(milliseconds=index)
        record = deepcopy(sample)
        record["created"] = to_iso_z(created)
        record[TEST_RUN_ID_FIELD] = run_id
        message = record.get("message")
        if isinstance(message, dict):
            message["timestamp"] = to_iso_z(created)
        records.append(record)

    return records


def _build_connection_unique_records(run_id: str, unique_records: int) -> list[dict[str, object]]:
    sample = load_sample(CONNECTION_SAMPLE_PATH)
    start_at = base_test_time()
    records: list[dict[str, object]] = []
    base_id = str(sample.get("id", "connection"))

    for index in range(unique_records):
        connected = start_at + timedelta(milliseconds=index)
        disconnected = connected + timedelta(seconds=30)
        record = deepcopy(sample)
        record["id"] = f"{base_id}-{index}"
        record["connected"] = to_iso_z(connected)
        record["disconnected"] = to_iso_z(disconnected)
        record["created"] = to_iso_z(connected)
        record["updated"] = to_iso_z(disconnected)
        record["last_activity"] = to_iso_z(connected + timedelta(seconds=3))
        record["duration"] = 30
        record[TEST_RUN_ID_FIELD] = run_id
        records.append(record)

    return records


def _build_source_records(unique_records: list[dict[str, object]], duplicate_records: int) -> list[dict[str, object]]:
    source_records = list(unique_records)
    unique_len = len(unique_records)
    # Duplicate records are spread through the source result set so they hit different pages.
    for duplicate_index in range(duplicate_records):
        source_idx = (duplicate_index * 7) % unique_len
        insert_idx = (duplicate_index * 3) % (len(source_records) + 1)
        source_records.insert(insert_idx, deepcopy(unique_records[source_idx]))
    return source_records


def _run_source(source: str, scenario: Scenario, config: SyncConfig) -> None:
    source_config = resolve_source_config(config, source)
    run_id = str(uuid4())
    source_label = "AUDIT-EVENT" if source == "audit" else "CONNECTION"
    unique_records = (
        _build_audit_unique_records(run_id, scenario.unique_records)
        if source == "audit"
        else _build_connection_unique_records(run_id, scenario.unique_records)
    )
    source_records = _build_source_records(unique_records, scenario.duplicate_records)
    started = perf_counter()

    try:
        if source == "audit":
            enabled_event_ids = {str(unique_records[0].get("event_id", ""))}

            def _fake_get_audit_events(
                api: object,
                start_time: str | None = None,
                end_time: str | None = None,
                sort_dir: str = "asc",
                sort_key: str = "created",
                limit: int | None = None,
                offset: int = 0,
                propagate_errors: bool = False,
            ) -> dict[str, object]:
                del api, start_time, end_time, sort_dir, sort_key, propagate_errors
                page_size = len(source_records) if limit is None else limit
                if offset >= len(source_records):
                    return {"count": len(source_records), "items": []}
                end_offset = min(offset + page_size, len(source_records))
                return {"count": len(source_records), "items": source_records[offset:end_offset]}

            with (
                patch(
                    "lib.database.sync.time_series.sources.audit.report_api.get_audit_events",
                    side_effect=_fake_get_audit_events,
                ),
                patch(
                    "lib.database.sync.time_series.sources.audit._get_enabled_event_ids",
                    return_value=enabled_event_ids,
                ),
                patch("lib.database.sync.time_series.manager.get_latest_timestamp", return_value=None),
            ):
                sync_audit_events(
                    api=object(),
                    range_minutes=source_config.range_minutes,
                    batch_size=scenario.batch_size,
                    max_range_hours=config.max_range_hours,
                    window_sizes_minutes=config.window_sizes_minutes,
                    max_records_per_window=config.max_records_per_window,
                    window_size_down_minutes=config.window_size_down_minutes,
                )
        else:

            def _fake_search_connections(
                api: object,
                offset: int = 0,
                limit: int | None = None,
                sort_key: str | None = None,
                sort_dir: str | None = None,
                search_payload: dict[str, object] | None = None,
                propagate_errors: bool = False,
            ) -> dict[str, object]:
                del api, sort_key, sort_dir, search_payload, propagate_errors
                page_size = len(source_records) if limit is None else limit
                if offset >= len(source_records):
                    return {"count": len(source_records), "items": []}
                end_offset = min(offset + page_size, len(source_records))
                return {"count": len(source_records), "items": source_records[offset:end_offset]}

            with (
                patch(
                    "lib.database.sync.time_series.sources.connection.report_api.search_connections",
                    side_effect=_fake_search_connections,
                ),
                patch("lib.database.sync.time_series.manager.get_latest_timestamp", return_value=None),
            ):
                sync_connections(
                    api=object(),
                    range_minutes=source_config.range_minutes,
                    batch_size=scenario.batch_size,
                    max_range_hours=config.max_range_hours,
                    window_sizes_minutes=config.window_sizes_minutes,
                    max_records_per_window=config.max_records_per_window,
                    window_size_down_minutes=config.window_size_down_minutes,
                )

        stats = _fetch_integrity_stats(source, run_id)
        _assert_integrity(source, len(source_records), scenario.unique_records, stats)
        duration_seconds = perf_counter() - started
        filtered_records = len(source_records) - stats.total_rows
        expectations = [
            (
                "Insert count matches expected unique records",
                f"{stats.total_rows} == {scenario.unique_records}",
            ),
            (
                "No duplicate recordId groups persisted",
                f"{stats.duplicate_record_ids} == 0",
            ),
            (
                "Duplicate source records were filtered",
                f"{stats.total_rows} < {len(source_records)}",
            ),
        ]

        print()
        print("=" * 76)
        print(f"{source_label} - INTEGRITY TEST SUMMARY")
        print("-" * 76)
        print(f"Source records:    {len(source_records)}")
        print(f"Expected inserted: {scenario.unique_records}")
        print(f"Inserted rows:     {stats.total_rows}")
        print(f"Filtered duplicates: {filtered_records}")
        print(f"Duplicate groups:  {stats.duplicate_record_ids}")
        print(f"Batch size:        {scenario.batch_size}")
        print(f"Duration:          {duration_seconds:.3f} s")
        print()
        print("Expectations (PASS):")
        for label, detail in expectations:
            print(f"  [PASS] {label} ({detail})")
        print("=" * 76)
        print()
    finally:
        cleanup_run_data(source, run_id)


def main() -> None:
    config = SyncConfig()
    init_data_tables(config)
    run_started_at = datetime.now(UTC)
    started_counter = perf_counter()

    print("Running deterministic integrity checks for audit and connection sync paths")
    _run_source("audit", AUDIT_SCENARIO, config)
    _run_source("connection", CONNECTION_SCENARIO, config)
    run_ended_at = datetime.now(UTC)
    wall_duration_seconds = perf_counter() - started_counter

    print("=" * 76)
    print("INTEGRITY TEST RUN SUMMARY")
    print("-" * 76)
    print(f"Begin:             {run_started_at.isoformat().replace('+00:00', 'Z')}")
    print(f"End:               {run_ended_at.isoformat().replace('+00:00', 'Z')}")
    print(f"Wall time:         {wall_duration_seconds:.3f} s")
    print("Result:            PASS")
    print("=" * 76)
    print()


if __name__ == "__main__":
    main()
