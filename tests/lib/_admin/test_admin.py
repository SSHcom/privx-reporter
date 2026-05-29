"""Tests for admin command dispatcher."""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from lib._admin import admin as admin_module


@pytest.mark.unit
@patch("administration.event.handle")
def test_run_valid_command(mock_handle: MagicMock) -> None:
    """Dispatches valid command module handler."""
    mock_config: dict[str, object] = {"event": {}}
    mock_args = argparse.Namespace(command="event", subcommand="enable", code="AUDIT_001")

    admin_module.run(mock_args, mock_config)

    mock_handle.assert_called_once_with(mock_args, mock_config)


@pytest.mark.unit
def test_run_invalid_command() -> None:
    """Returns error payload for unknown command."""
    mock_config: dict[str, object] = {}
    mock_args = argparse.Namespace(command="not-a-command")

    result = admin_module.run(mock_args, mock_config)

    assert result == {
        "error_message": "Invalid admin command 'not-a-command'",
        "info_message": None,
    }
