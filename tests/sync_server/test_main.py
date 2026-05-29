"""Tests for sync_server main loop orchestration."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

import pytest

from lib.env_sync import AUDIT_EVENT_SOURCE, CONCURRENT_SOURCE, CONNECTION_SOURCE, TREND_SOURCE
from sync_server.main import _sync_trend_daily_if_due, main


@dataclass
class _SourceConfig:
    minutes: int
    range_minutes: int
    retention_days: int


@pytest.mark.unit
def test_main_runs_only_configured_source() -> None:
    config = MagicMock()
    config.sources = [AUDIT_EVENT_SOURCE]
    config.batch_size = 100
    config.sync_trend_hour = None
    config.audit_event_config = _SourceConfig(minutes=1, range_minutes=30, retention_days=7)
    config.connection_config = _SourceConfig(minutes=1, range_minutes=30, retention_days=7)

    with (
        patch("sync_server.main.SyncConfig", return_value=config),
        patch("sync_server.main.init_databases"),
        patch("sync_server.main.get_privx_client", return_value=MagicMock()),
        patch("sync_server.main.sync_audit_events") as mock_sync_audit_events,
        patch("sync_server.main.sync_connections") as mock_sync_connections,
        patch("sync_server.main.time.time", return_value=120.0),
        patch("sync_server.main.time.sleep", side_effect=KeyboardInterrupt),
    ):
        main()

    mock_sync_audit_events.assert_called_once()
    mock_sync_connections.assert_not_called()


@pytest.mark.unit
def test_main_exits_with_code_1_on_db_init_error() -> None:
    config = MagicMock()
    config.sources = [AUDIT_EVENT_SOURCE, CONNECTION_SOURCE]
    config.batch_size = 100
    config.sync_trend_hour = None
    config.audit_event_config = _SourceConfig(minutes=1, range_minutes=30, retention_days=7)
    config.connection_config = _SourceConfig(minutes=1, range_minutes=30, retention_days=7)

    with (
        patch("sync_server.main.SyncConfig", return_value=config),
        patch("sync_server.main.init_databases", side_effect=RuntimeError("db down")),
        patch("sync_server.main.sys.exit", side_effect=SystemExit(1)) as mock_exit,
    ):
        with pytest.raises(SystemExit):
            main()

    mock_exit.assert_called_once_with(1)


@pytest.mark.unit
def test_main_recovers_from_sync_cycle_exception() -> None:
    config = MagicMock()
    config.sources = [AUDIT_EVENT_SOURCE]
    config.batch_size = 100
    config.sync_trend_hour = None
    config.audit_event_config = _SourceConfig(minutes=1, range_minutes=30, retention_days=7)
    config.connection_config = _SourceConfig(minutes=1, range_minutes=30, retention_days=7)
    config.max_range_hours = None

    with (
        patch("sync_server.main.SyncConfig", return_value=config),
        patch("sync_server.main.init_databases"),
        patch("sync_server.main.get_privx_client", return_value=MagicMock()),
        patch("sync_server.main.sync_audit_events", side_effect=[RuntimeError("boom"), None]) as mock_sync,
        patch("sync_server.main.sync_connections"),
        patch("sync_server.main.time.time", side_effect=[120.0, 190.0]),
        patch("sync_server.main.time.sleep", side_effect=[None, KeyboardInterrupt]),
    ):
        main()

    assert mock_sync.call_count == 2


@pytest.mark.unit
@pytest.mark.parametrize(
    ("now_utc", "should_run"),
    [
        (datetime(2026, 4, 27, 1, 10, tzinfo=UTC), True),
        (datetime(2026, 4, 27, 0, 10, tzinfo=UTC), False),
        (datetime(2026, 4, 27, 3, 10, tzinfo=UTC), True),
    ],
)
def test_main_trend_sync_scheduling(now_utc: datetime, should_run: bool) -> None:
    config = MagicMock()
    config.sources = []
    config.batch_size = 100
    config.max_range_hours = None
    config.sync_trend_hour = 1
    config.audit_event_config = _SourceConfig(minutes=1, range_minutes=30, retention_days=7)
    config.connection_config = _SourceConfig(minutes=1, range_minutes=30, retention_days=7)

    with (
        patch("sync_server.main.SyncConfig", return_value=config),
        patch("sync_server.main.init_databases"),
        patch("sync_server.main.get_privx_client", return_value=MagicMock()),
        patch("sync_server.main.sync_audit_events"),
        patch("sync_server.main.sync_connections"),
        patch("sync_server.main.run_trend_sync") as mock_trend_sync,
        patch("sync_server.main.time.time", return_value=120.0),
        patch(
            "sync_server.main.datetime",
            new=MagicMock(
                now=MagicMock(return_value=now_utc),
                combine=datetime.combine,
            ),
        ),
        patch("sync_server.main.time.sleep", side_effect=KeyboardInterrupt),
    ):
        main()

    if should_run:
        mock_trend_sync.assert_called_once()
    else:
        mock_trend_sync.assert_not_called()


@pytest.mark.unit
def test_main_runs_trend_before_audit_when_configured_first() -> None:
    config = MagicMock()
    config.sources = [TREND_SOURCE, AUDIT_EVENT_SOURCE]
    config.batch_size = 100
    config.max_range_hours = None
    config.sync_trend_hour = 1
    config.audit_event_config = _SourceConfig(minutes=1, range_minutes=30, retention_days=7)
    config.connection_config = _SourceConfig(minutes=1, range_minutes=30, retention_days=7)

    call_order: list[str] = []

    with (
        patch("sync_server.main.SyncConfig", return_value=config),
        patch("sync_server.main.init_databases"),
        patch("sync_server.main.get_privx_client", return_value=MagicMock()),
        patch(
            "sync_server.main.run_trend_sync",
            side_effect=lambda *args, **kwargs: call_order.append("trends") or MagicMock(),
        ),
        patch(
            "sync_server.main.sync_audit_events",
            side_effect=lambda *args, **kwargs: call_order.append("audit"),
        ),
        patch("sync_server.main.sync_connections"),
        patch("sync_server.main.time.time", return_value=120.0),
        patch(
            "sync_server.main.datetime",
            new=MagicMock(
                now=MagicMock(return_value=datetime(2026, 4, 27, 1, 10, tzinfo=UTC)),
                combine=datetime.combine,
            ),
        ),
        patch("sync_server.main.time.sleep", side_effect=KeyboardInterrupt),
    ):
        main()

    assert call_order == ["trends", "audit"]


@pytest.mark.unit
def test_main_rejects_unsupported_source() -> None:
    config = MagicMock()
    config.sources = ["bogus"]
    config.batch_size = 100
    config.max_range_hours = None
    config.sync_trend_hour = None
    config.audit_event_config = _SourceConfig(minutes=1, range_minutes=30, retention_days=7)
    config.connection_config = _SourceConfig(minutes=1, range_minutes=30, retention_days=7)

    with (
        patch("sync_server.main.SyncConfig", return_value=config),
        patch("sync_server.main.init_databases"),
        patch("sync_server.main.get_privx_client", return_value=MagicMock()),
        patch("sync_server.main.logger.error") as mock_logger_error,
        patch("sync_server.main.time.time", return_value=120.0),
        patch("sync_server.main.time.sleep", side_effect=KeyboardInterrupt),
    ):
        main()

    assert any("Unsupported sync source configured" in call.args[0] for call in mock_logger_error.call_args_list)


@pytest.mark.unit
def test_main_starts_concurrent_stats_thread_when_source_enabled() -> None:
    config = MagicMock()
    config.sources = [CONCURRENT_SOURCE]
    config.batch_size = 100
    config.max_range_hours = None
    config.sync_trend_hour = None
    config.audit_event_config = _SourceConfig(minutes=1, range_minutes=30, retention_days=7)
    config.connection_config = _SourceConfig(minutes=1, range_minutes=30, retention_days=7)

    mock_thread = MagicMock()
    with (
        patch("sync_server.main.SyncConfig", return_value=config),
        patch("sync_server.main.init_databases"),
        patch("sync_server.main.get_privx_client", return_value=MagicMock()),
        patch("sync_server.main.threading.Thread", return_value=mock_thread) as mock_thread_class,
        patch("sync_server.main.time.time", return_value=120.0),
        patch("sync_server.main.time.sleep", side_effect=KeyboardInterrupt),
    ):
        main()

    mock_thread_class.assert_called_once()
    assert mock_thread_class.call_args.kwargs["daemon"] is True
    assert mock_thread_class.call_args.kwargs["name"] == "concurrent-stats"
    mock_thread.start.assert_called_once_with()


@pytest.mark.unit
def test_sync_trend_daily_if_due_logs_and_returns_today_on_failure() -> None:
    with (
        patch(
            "sync_server.main.datetime",
            new=MagicMock(
                now=MagicMock(return_value=datetime(2026, 4, 27, 1, 10, tzinfo=UTC)),
                combine=datetime.combine,
            ),
        ),
        patch("sync_server.main.run_trend_sync", side_effect=RuntimeError("boom")),
        patch("sync_server.main.logger.error") as mock_logger_error,
    ):
        last_sync = _sync_trend_daily_if_due(
            trend_hour_utc=1,
            last_sync_date=None,
            api=MagicMock(),
        )

    assert last_sync == date(2026, 4, 27)
    mock_logger_error.assert_called_once()
