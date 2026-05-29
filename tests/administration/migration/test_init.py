"""Tests for administration migration package handler routing."""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from administration.migration import handle


@pytest.mark.unit
@patch("administration.migration.handle_up_migration")
def test_handle_routes_up(mock_handle_up: MagicMock) -> None:
    mock_handle_up.return_value = {"error_message": None, "info_message": "ok"}
    result = handle(argparse.Namespace(subcommand="up"), {})
    assert result == {"error_message": None, "info_message": "ok"}
    mock_handle_up.assert_called_once()


@pytest.mark.unit
@patch("administration.migration.handle_down_migration")
def test_handle_routes_down(mock_handle_down: MagicMock) -> None:
    mock_handle_down.return_value = {"error_message": None, "info_message": "ok"}
    result = handle(argparse.Namespace(subcommand="down"), {})
    assert result == {"error_message": None, "info_message": "ok"}
    mock_handle_down.assert_called_once()


@pytest.mark.unit
@patch("administration.migration.handle_status_migration")
def test_handle_routes_status(mock_handle_status: MagicMock) -> None:
    mock_handle_status.return_value = {"error_message": None, "info_message": "ok"}
    result = handle(argparse.Namespace(subcommand="status"), {})
    assert result == {"error_message": None, "info_message": "ok"}
    mock_handle_status.assert_called_once()


@pytest.mark.unit
def test_handle_returns_error_for_invalid_subcommand() -> None:
    result = handle(argparse.Namespace(subcommand="unknown"), {})
    assert result == {
        "error_message": "Invalid migration subcommand 'unknown'",
        "info_message": None,
    }
