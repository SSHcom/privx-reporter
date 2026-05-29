"""Tests for sync trend administration command."""

import argparse
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from administration.sync.trend.module import handle_trend_sync


@pytest.mark.unit
@patch(
    "administration.sync.trend.module.run_trend_sync",
    return_value=SimpleNamespace(
        placeholder_rows=2,
        days=90,
        today_inserted=True,
    ),
)
@patch("administration.sync.trend.module.init_databases")
def test_trend_sync_upserts_row(
    mock_init_databases: MagicMock,
    mock_run_trend_sync: MagicMock,
) -> None:
    result = handle_trend_sync(argparse.Namespace(days=90), {})

    assert result["error_message"] is None
    assert result["info_message"] == "Filled 2 placeholder rows for past 90 day(s); today inserted: True."
    mock_init_databases.assert_called_once_with()
    mock_run_trend_sync.assert_called_once_with(days=90)


@pytest.mark.unit
def test_trend_sync_returns_error_for_invalid_days() -> None:
    result = handle_trend_sync(argparse.Namespace(days=0), {})

    assert "--days must be a positive integer." in (result["error_message"] or "")
    assert result["info_message"] is None
