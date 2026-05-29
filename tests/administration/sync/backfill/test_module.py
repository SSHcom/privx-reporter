"""Tests for sync backfill administration command."""

import argparse
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from administration.sync.backfill.module import handle_backfill


@pytest.mark.unit
@patch("administration.sync.backfill.module.backfill_connections", return_value=4)
@patch("administration.sync.backfill.module.backfill_audit_events", return_value=3)
@patch("administration.sync.backfill.module.get_privx_client", return_value=MagicMock())
@patch("administration.sync.backfill.module.init_databases")
@patch("administration.sync.backfill.module.calculate_backfill_range")
@patch("administration.sync.backfill.module.SyncConfig")
def test_backfill_uses_sync_env_defaults(
    mock_sync_config: MagicMock,
    mock_range: MagicMock,
    _mock_init_db: MagicMock,
    _mock_client: MagicMock,
    mock_backfill_audit: MagicMock,
    mock_backfill_connections: MagicMock,
) -> None:
    start_time = datetime(2026, 4, 1, tzinfo=UTC)
    end_time = datetime(2026, 4, 2, tzinfo=UTC)
    mock_range.return_value = (start_time, end_time)
    mock_sync_config.return_value = SimpleNamespace(
        sources=["audit", "connection"],
        batch_size=777,
        window_sizes_minutes=[5, 10, 15],
        max_records_per_window=55_000,
        window_size_down_minutes=5,
    )

    result = handle_backfill(argparse.Namespace(days=1, from_date=None, source="all", batch_size=None), {})

    assert result["error_message"] is None
    mock_backfill_audit.assert_called_once_with(
        _mock_client.return_value,
        start_time,
        end_time,
        batch_size=777,
        window_sizes_minutes=[5, 10, 15],
        max_records_per_window=55_000,
        window_size_down_minutes=5,
    )
    mock_backfill_connections.assert_called_once_with(
        _mock_client.return_value,
        start_time,
        end_time,
        batch_size=777,
        window_sizes_minutes=[5, 10, 15],
        max_records_per_window=55_000,
        window_size_down_minutes=5,
    )


@pytest.mark.unit
@patch("administration.sync.backfill.module.backfill_connections", return_value=4)
@patch("administration.sync.backfill.module.backfill_audit_events", return_value=3)
@patch("administration.sync.backfill.module.get_privx_client", return_value=MagicMock())
@patch("administration.sync.backfill.module.init_databases")
@patch("administration.sync.backfill.module.calculate_backfill_range")
@patch("administration.sync.backfill.module.SyncConfig")
def test_backfill_all_respects_configured_source_order(
    mock_sync_config: MagicMock,
    mock_range: MagicMock,
    _mock_init_db: MagicMock,
    _mock_client: MagicMock,
    mock_backfill_audit: MagicMock,
    mock_backfill_connections: MagicMock,
) -> None:
    start_time = datetime(2026, 4, 1, tzinfo=UTC)
    end_time = datetime(2026, 4, 2, tzinfo=UTC)
    mock_range.return_value = (start_time, end_time)
    mock_sync_config.return_value = SimpleNamespace(
        sources=["connection", "audit"],
        batch_size=777,
        window_sizes_minutes=[5, 10, 15],
        max_records_per_window=55_000,
        window_size_down_minutes=5,
    )
    execution_order: list[str] = []
    mock_backfill_connections.side_effect = lambda *args, **kwargs: execution_order.append("connection") or 4
    mock_backfill_audit.side_effect = lambda *args, **kwargs: execution_order.append("audit") or 3

    result = handle_backfill(argparse.Namespace(days=1, from_date=None, source="all", batch_size=None), {})

    assert result["error_message"] is None
    assert mock_backfill_connections.call_count == 1
    assert mock_backfill_audit.call_count == 1
    assert execution_order == ["connection", "audit"]
