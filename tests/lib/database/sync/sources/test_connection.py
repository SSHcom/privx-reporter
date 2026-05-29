"""Tests for connection sync source."""

from unittest.mock import MagicMock, patch

import pytest

from lib.database.sync.time_series.sources.connection import ConnectionSync, _build_connection_record_id


@pytest.mark.unit
def test_build_connection_record_id_requires_id_and_connected() -> None:
    assert (
        _build_connection_record_id({"id": "conn-1", "connected": "2026-01-01T00:00:00Z"})
        == "conn-1|2026-01-01T00:00:00Z"
    )
    assert _build_connection_record_id({"id": "conn-1"}) is None
    assert _build_connection_record_id({"connected": "2026-01-01T00:00:00Z"}) is None


@pytest.mark.unit
@patch("lib.database.sync.time_series.sources.connection.report_api.search_connections")
def test_fetch_batch_uses_propagate_errors(mock_search_connections: MagicMock, mock_api: MagicMock) -> None:
    source = ConnectionSync()
    mock_search_connections.return_value = {"items": [{"id": "1"}], "count": 99}

    result = source.fetch_batch(
        api=mock_api,
        start_time="2026-01-01T00:00:00Z",
        end_time="2026-01-01T01:00:00Z",
        offset=10,
        limit=20,
    )

    assert result.count == 1
    assert len(result.items) == 1
    kwargs = mock_search_connections.call_args.kwargs
    assert kwargs["propagate_errors"] is True
    assert kwargs["offset"] == 10
    assert kwargs["limit"] == 20
    assert kwargs["search_payload"]["connected"]["start"] == "2026-01-01T00:00:00Z"
    assert kwargs["search_payload"]["connected"]["end"] == "2026-01-01T01:00:00Z"
