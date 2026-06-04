import argparse
import logging
from datetime import UTC, datetime
from typing import Any

from lib.clients.privx import get_privx_client
from lib.database import init_databases
from lib.database.sync import backfill_audit_events, backfill_connections
from lib.database.sync.time_series.helpers import calculate_backfill_range
from lib.env_sync import SyncConfig

logger = logging.getLogger(__name__)
VALID_SOURCES = {"audit", "connection", "all"}


def _parse_date(date_str: str) -> datetime:
    """Parse a date string in YYYY-MM-DD format to a timezone-aware datetime."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=UTC)
    except ValueError as e:
        raise ValueError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD.") from e


def handle_backfill(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, str | None]:
    """Handle sync backfill action."""
    _ = config

    try:
        sync_config = SyncConfig()
    except Exception as e:
        logger.error(f"Failed to load sync configuration: {e}", exc_info=True)
        return {"error_message": f"Failed to load sync configuration: {e}", "info_message": None}

    days = getattr(args, "days", None)
    from_date_str = getattr(args, "from_date", None)
    source = getattr(args, "source", "all")
    batch_size = getattr(args, "batch_size", sync_config.batch_size)

    if days is not None:
        days = int(days)

    if batch_size is not None:
        batch_size = int(batch_size)
    else:
        batch_size = sync_config.batch_size

    if source not in VALID_SOURCES:
        return {
            "error_message": f"Invalid source '{source}'. Valid options: {', '.join(sorted(VALID_SOURCES))}",
            "info_message": None,
        }

    if days is None and from_date_str is None:
        return {"error_message": "Either --days or --from must be provided.", "info_message": None}

    if days is not None and from_date_str is not None:
        return {"error_message": "Cannot specify both --days and --from.", "info_message": None}

    from_date = None
    if from_date_str is not None:
        try:
            from_date = _parse_date(from_date_str)
        except ValueError as e:
            return {"error_message": str(e), "info_message": None}

    try:
        start_time, end_time = calculate_backfill_range(days=days, from_date=from_date)
    except ValueError as e:
        return {"error_message": str(e), "info_message": None}

    logger.info(f"Backfill range: {start_time.isoformat()} to {end_time.isoformat()}")
    logger.info(f"Source: {source}")
    logger.info(f"Batch size: {batch_size}")

    try:
        init_databases()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        return {"error_message": f"Database initialization failed: {e}", "info_message": None}

    try:
        api = get_privx_client()
        logger.info("Successfully connected to PrivX API")
    except Exception as e:
        logger.error(f"Failed to connect to PrivX API: {e}", exc_info=True)
        return {"error_message": f"Failed to connect to PrivX API: {e}", "info_message": None}

    if source == "all":
        selected_sources = list(sync_config.sources)
    else:
        selected_sources = [source]

    total_by_source = {"audit": 0, "connection": 0}

    try:
        for selected_source in selected_sources:
            if selected_source == "audit":
                total_by_source["audit"] = backfill_audit_events(
                    api,
                    start_time,
                    end_time,
                    batch_size=batch_size,
                    window_sizes_minutes=sync_config.window_sizes_minutes,
                    max_records_per_window=sync_config.max_records_per_window,
                    window_size_down_minutes=sync_config.window_size_down_minutes,
                )
            elif selected_source == "connection":
                total_by_source["connection"] = backfill_connections(
                    api,
                    start_time,
                    end_time,
                    batch_size=batch_size,
                    window_sizes_minutes=sync_config.window_sizes_minutes,
                    max_records_per_window=sync_config.max_records_per_window,
                    window_size_down_minutes=sync_config.window_size_down_minutes,
                )
            else:
                raise ValueError(f"Unsupported sync source configured: {selected_source}")

    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        return {"error_message": f"Backfill failed: {e}", "info_message": None}

    summary_parts = []
    if "audit" in selected_sources:
        summary_parts.append(f"{total_by_source['audit']} audit events")
    if "connection" in selected_sources:
        summary_parts.append(f"{total_by_source['connection']} connections")

    summary = f"Backfill complete. Inserted: {', '.join(summary_parts)}."
    return {"error_message": None, "info_message": summary}
