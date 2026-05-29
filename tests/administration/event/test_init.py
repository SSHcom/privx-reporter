"""Tests for administration event package handler routing."""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from administration.event import handle


@pytest.mark.unit
@patch("administration.event.handle_enable_event")
def test_handle_routes_enable(mock_handle_enable: MagicMock) -> None:
    mock_handle_enable.return_value = {"error_message": None, "info_message": "ok"}
    result = handle(argparse.Namespace(subcommand="enable"), {})
    assert result == {"error_message": None, "info_message": "ok"}
    mock_handle_enable.assert_called_once()


@pytest.mark.unit
@patch("administration.event.handle_disable_event")
def test_handle_routes_disable(mock_handle_disable: MagicMock) -> None:
    mock_handle_disable.return_value = {"error_message": None, "info_message": "ok"}
    result = handle(argparse.Namespace(subcommand="disable"), {})
    assert result == {"error_message": None, "info_message": "ok"}
    mock_handle_disable.assert_called_once()


@pytest.mark.unit
@patch("administration.event.handle_list_event")
def test_handle_routes_list(mock_handle_list: MagicMock) -> None:
    mock_handle_list.return_value = {"error_message": None, "info_message": "ok"}
    result = handle(argparse.Namespace(subcommand="list"), {})
    assert result == {"error_message": None, "info_message": "ok"}
    mock_handle_list.assert_called_once()


@pytest.mark.unit
def test_handle_returns_error_for_invalid_subcommand() -> None:
    result = handle(argparse.Namespace(subcommand="unknown"), {})
    assert result == {
        "error_message": "Invalid event subcommand 'unknown'",
        "info_message": None,
    }
