"""Database sync operations for pulling data from PrivX API."""

from datetime import datetime

from .time_series.manager import SyncManager
from .time_series.sources import AuditEventSync, ConnectionSync
from .trend import TrendSyncSummary, run_trend_sync

_audit_manager = SyncManager(AuditEventSync())
_connection_manager = SyncManager(ConnectionSync())


def sync_audit_events(
    api: object,
    range_minutes: int,
    batch_size: int,
    max_range_hours: int | None = None,
    *,
    window_sizes_minutes: list[int],
    max_records_per_window: int,
    window_size_down_minutes: int,
) -> int:
    return _audit_manager.sync(
        api,
        range_minutes,
        batch_size,
        max_range_hours=max_range_hours,
        window_sizes_minutes=window_sizes_minutes,
        max_records_per_window=max_records_per_window,
        window_size_down_minutes=window_size_down_minutes,
    )


def sync_connections(
    api: object,
    range_minutes: int,
    batch_size: int,
    max_range_hours: int | None = None,
    *,
    window_sizes_minutes: list[int],
    max_records_per_window: int,
    window_size_down_minutes: int,
) -> int:
    return _connection_manager.sync(
        api,
        range_minutes,
        batch_size,
        max_range_hours=max_range_hours,
        window_sizes_minutes=window_sizes_minutes,
        max_records_per_window=max_records_per_window,
        window_size_down_minutes=window_size_down_minutes,
    )


def backfill_audit_events(
    api: object,
    start_time: datetime,
    end_time: datetime,
    batch_size: int,
    *,
    window_sizes_minutes: list[int],
    max_records_per_window: int,
    window_size_down_minutes: int,
) -> int:
    return _audit_manager.backfill(
        api,
        start_time,
        end_time,
        batch_size=batch_size,
        window_sizes_minutes=window_sizes_minutes,
        max_records_per_window=max_records_per_window,
        window_size_down_minutes=window_size_down_minutes,
    )


def backfill_connections(
    api: object,
    start_time: datetime,
    end_time: datetime,
    batch_size: int,
    *,
    window_sizes_minutes: list[int],
    max_records_per_window: int,
    window_size_down_minutes: int,
) -> int:
    return _connection_manager.backfill(
        api,
        start_time,
        end_time,
        batch_size=batch_size,
        window_sizes_minutes=window_sizes_minutes,
        max_records_per_window=max_records_per_window,
        window_size_down_minutes=window_size_down_minutes,
    )


__all__ = [
    "backfill_audit_events",
    "backfill_connections",
    "sync_audit_events",
    "sync_connections",
    "run_trend_sync",
    "TrendSyncSummary",
]
