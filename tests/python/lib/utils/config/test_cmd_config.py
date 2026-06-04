"""Tests for command configuration utilities."""

import pytest

from lib._report.error import ConfigError
from lib.utils.config.cmd_config import get_subcommand_config


@pytest.mark.unit
def test_get_subcommand_config_success() -> None:
    """Test getting subcommand config returns full config."""
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": "true|User ID",
                    }
                }
            }
        }
    }

    result = get_subcommand_config(config, "access", "map")

    assert result is config
    assert result["access"]["subcommands"]["map"]["fields"]["user_id"] == "true|User ID"


@pytest.mark.unit
def test_get_subcommand_config_missing_group() -> None:
    """Test that missing group raises ConfigError."""
    config = {
        "other": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": "true|User ID",
                    }
                }
            }
        }
    }

    with pytest.raises(ConfigError, match="Output configuration not found for access map"):
        get_subcommand_config(config, "access", "map")


@pytest.mark.unit
def test_get_subcommand_config_missing_subcommand() -> None:
    """Test that missing subcommand raises ConfigError."""
    config = {
        "access": {
            "subcommands": {
                "other": {
                    "fields": {
                        "user_id": "true|User ID",
                    }
                }
            }
        }
    }

    with pytest.raises(ConfigError, match="Output configuration not found for access map"):
        get_subcommand_config(config, "access", "map")
