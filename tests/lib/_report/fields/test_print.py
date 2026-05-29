"""Tests for field print functionality."""

from unittest.mock import MagicMock, patch

import pytest

from lib._report.error import ConfigError
from lib._report.fields.print import print_available_fields_and_exit


@pytest.mark.unit
@patch("lib._report.fields.print.sys.exit")
def test_print_available_fields_and_exit_success(mock_exit: MagicMock) -> None:
    """Test listing available fields displays correctly."""
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": "true|User ID",
                        "role_name": "true|Role Name",
                        "target_hosts": "false|Target Hosts",
                        "email": "redact|Email",
                    }
                }
            }
        }
    }

    with patch("builtins.print") as mock_print:
        print_available_fields_and_exit(config, "access.subcommands.map")

    # Check that exit was called
    mock_exit.assert_called_once_with(0)

    # Check that print was called (we can't easily check exact output due to formatting)
    assert mock_print.call_count > 0


@pytest.mark.unit
def test_print_available_fields_and_exit_no_fields() -> None:
    """Test listing available fields when no fields are available."""
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "email": "redact|Email",
                    }
                }
            }
        }
    }

    with pytest.raises(ConfigError, match="No available fields found"):
        print_available_fields_and_exit(config, "access.subcommands.map")


@pytest.mark.unit
def test_print_available_fields_and_exit_invalid_config() -> None:
    """Test listing available fields with invalid config."""
    with pytest.raises(ValueError, match="Configuration dictionary is empty or None"):
        print_available_fields_and_exit({}, "access.subcommands.map")
