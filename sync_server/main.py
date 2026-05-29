"""Sync server that syncs time-series data from remote database.

Tests are not necessary for this module.
"""

import logging
import sys
import threading
import time
from datetime import UTC, date, datetime
from datetime import time as dt_time

from lib.clients.privx import get_privx_client
from lib.database import init_databases
from lib.database.sync import run_trend_sync, sync_audit_events, sync_connections
from lib.database.sync.concurrent import sync_concurrent_stats
from lib.database.sync.trend import DEFAULT_TREND_DAYS, TrendAPI
from lib.env_sync import (
    AUDIT_EVENT_SOURCE,
    CONCURRENT_SOURCE,
    CONNECTION_SOURCE,
    TREND_SOURCE,
    SyncConfig,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


def _sync_trend_daily_if_due(
    *,
    trend_hour_utc: int | None,
    last_sync_date: date | None,
    api: TrendAPI | None = None,
) -> date | None:
    """Run trend sync once per UTC day when configured hour is reached or passed."""
    if trend_hour_utc is None:
        return last_sync_date

    now_utc = datetime.now(UTC)
    today = now_utc.date()
    scheduled_time = datetime.combine(today, dt_time(hour=trend_hour_utc), tzinfo=UTC)

    if now_utc < scheduled_time or last_sync_date == today:
        return last_sync_date

    try:
        summary = run_trend_sync(
            days=DEFAULT_TREND_DAYS,
            api=api,
        )
    except Exception as error:
        logger.error("Trend sync failed: %s", error, exc_info=True)
    else:
        logger.info(
            "Filled %s placeholder rows for past %s day(s); today inserted: %s.",
            summary.placeholder_rows,
            summary.days,
            summary.today_inserted,
        )

    return today


def main() -> None:
    """Main server loop."""
    logger.info("Starting sync server...")

    _stop_event = threading.Event()
    try:
        # Get sync configuration
        config = SyncConfig()
        audit_event_config = config.audit_event_config
        connection_config = config.connection_config
        assert audit_event_config is not None
        assert connection_config is not None

        # Log configuration values
        config.log_config_values()

        # Initialize database connections and apply pending migrations.
        try:
            init_databases()
        except Exception as e:
            logger.error(f"Database error: {e}", exc_info=True)
            sys.exit(1)

        # Create PrivX client
        api = get_privx_client()
        logger.info("Successfully connected to PrivX API")

        # Track last sync time for each source
        last_audit_sync = 0.0
        last_connection_sync = 0.0
        last_trend_sync_date: date | None = None

        # Start concurrent stats collection in a background thread (every 60s)
        if CONCURRENT_SOURCE in config.sources:

            def _concurrent_stats_loop() -> None:
                while not _stop_event.is_set():
                    try:
                        sync_concurrent_stats(api)
                    except Exception as e:
                        logger.error(f"Concurrent stats sync failed: {e}")
                    _stop_event.wait(60)

            concurrent_thread = threading.Thread(target=_concurrent_stats_loop, daemon=True, name="concurrent-stats")
            concurrent_thread.start()
            logger.info("Started concurrent stats background thread (60s interval)")

        # Main loop
        logger.info("Entering main loop...")

        while True:
            try:
                current_time = time.time()

                for source in config.sources:
                    if source not in (
                        TREND_SOURCE,
                        AUDIT_EVENT_SOURCE,
                        CONNECTION_SOURCE,
                        CONCURRENT_SOURCE,
                    ):
                        raise ValueError(f"Unsupported sync source configured: {source}")

                    if source == TREND_SOURCE:
                        last_trend_sync_date = _sync_trend_daily_if_due(
                            trend_hour_utc=config.sync_trend_hour,
                            last_sync_date=last_trend_sync_date,
                            api=api,
                        )

                    elif source == AUDIT_EVENT_SOURCE:
                        audit_interval_seconds = audit_event_config.minutes * 60
                        if current_time - last_audit_sync >= audit_interval_seconds:
                            sync_audit_events(
                                api,
                                audit_event_config.range_minutes,
                                config.batch_size,
                                max_range_hours=config.max_range_hours,
                                window_sizes_minutes=config.window_sizes_minutes,
                                max_records_per_window=config.max_records_per_window,
                                window_size_down_minutes=config.window_size_down_minutes,
                            )
                            last_audit_sync = current_time

                    elif source == CONNECTION_SOURCE:
                        connection_interval_seconds = connection_config.minutes * 60
                        if current_time - last_connection_sync >= connection_interval_seconds:
                            sync_connections(
                                api,
                                connection_config.range_minutes,
                                config.batch_size,
                                max_range_hours=config.max_range_hours,
                                window_sizes_minutes=config.window_sizes_minutes,
                                max_records_per_window=config.max_records_per_window,
                                window_size_down_minutes=config.window_size_down_minutes,
                            )
                            last_connection_sync = current_time

                if TREND_SOURCE not in config.sources:
                    last_trend_sync_date = _sync_trend_daily_if_due(
                        trend_hour_utc=config.sync_trend_hour,
                        last_sync_date=last_trend_sync_date,
                    )
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"Sync cycle failed: {e}", exc_info=True)

            time.sleep(5)

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        _stop_event.set()
        logger.info("Sync server stopped")


if __name__ == "__main__":
    main()
