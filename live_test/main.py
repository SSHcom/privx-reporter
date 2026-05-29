"""Sync-server load test runner."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from lib.env_sync import SyncConfig
from live_test._shared.common import RunMetrics, cleanup_run_data, init_data_tables, parse_args, resolve_source_config
from live_test.audit_event.runner import run as run_audit_event
from live_test.connection.runner import run as run_connection

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    args = parse_args()
    run_id = str(uuid4())

    config = SyncConfig()
    source_config = resolve_source_config(config, args.source)
    init_data_tables(config)

    logger.info(
        "Starting load test source=%s records=%s api_delay_ms=%s run_id=%s",
        args.source,
        args.records,
        args.api_delay_ms,
        run_id,
    )

    run_started_at = datetime.now(UTC)
    started_counter = perf_counter()
    run_metrics = RunMetrics()

    try:
        if args.source == "audit":
            run_metrics = run_audit_event(config, source_config, args.records, args.api_delay_ms, run_id)
        else:
            run_metrics = run_connection(config, source_config, args.records, args.api_delay_ms, run_id)
    finally:
        run_ended_at = datetime.now(UTC)
        wall_duration_seconds = perf_counter() - started_counter
        adjusted_duration_seconds = max(wall_duration_seconds - run_metrics.generation_seconds, 0.0)
        deleted_rows = cleanup_run_data(args.source, run_id)
        logger.info("Cleanup complete for run_id=%s. Deleted rows from %s table: %s", run_id, args.source, deleted_rows)

        records_per_second = args.records / adjusted_duration_seconds if adjusted_duration_seconds > 0 else 0.0
        start_str = run_started_at.isoformat().replace("+00:00", "Z")
        end_str = run_ended_at.isoformat().replace("+00:00", "Z")
        source_label = "AUDIT-EVENT" if args.source == "audit" else "CONNECTION"

        print()
        print("=" * 76)
        print(f"{source_label} - LOAD TEST RUN SUMMARY")
        print("-" * 76)
        print(f"Begin:            {start_str}")
        print(f"End:              {end_str}")
        print(f"Duration:         {adjusted_duration_seconds:.3f} s (generation excluded)")
        print(f"Generation time:  {run_metrics.generation_seconds:.3f} s")
        print(f"API wait time:    {run_metrics.api_wait_seconds:.3f} s")
        print(f"DB time:          {run_metrics.db_seconds:.3f} s")
        print(f"API delay:        {args.api_delay_ms} ms")
        print(f"Wall time:        {wall_duration_seconds:.3f} s")
        print(f"Batch size:       {config.batch_size}")
        if adjusted_duration_seconds > 0:
            api_pct = (run_metrics.api_wait_seconds / adjusted_duration_seconds) * 100
            db_pct = (run_metrics.db_seconds / adjusted_duration_seconds) * 100
            print(f"API/DB split:     API {api_pct:.1f}% | DB {db_pct:.1f}%")
        print(f"Records / second: {records_per_second:.2f}")
        print(f"Total records:    {args.records}")
        print("=" * 76)
        print()


if __name__ == "__main__":
    main()
