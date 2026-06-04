"""Tests for output field configuration reading and parsing."""

import pytest

from lib._report.fields.config import (
    get_available_fields,
    get_default_field_names,
)


@pytest.mark.unit
def test_get_available_fields_success() -> None:
    """Test getting available fields excludes redacted ones."""
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

    available_fields = get_available_fields(config, "access.subcommands.map")

    assert "user_id" in available_fields
    assert "role_name" in available_fields
    assert "target_hosts" in available_fields
    assert "email" not in available_fields
    assert available_fields["user_id"] == "User ID"
    assert available_fields["role_name"] == "Role Name"
    assert available_fields["target_hosts"] == "Target Hosts"


@pytest.mark.unit
def test_get_available_fields_empty_config() -> None:
    """Test that empty config raises ValueError."""
    with pytest.raises(ValueError, match="Configuration dictionary is empty or None"):
        get_available_fields({}, "access.subcommands.map")


@pytest.mark.unit
def test_get_available_fields_missing_path() -> None:
    """Test that missing config path raises ValueError."""
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

    with pytest.raises(ValueError, match="Configuration path access.subcommands.map not found"):
        get_available_fields(config, "access.subcommands.map")


@pytest.mark.unit
def test_get_available_fields_invalid_field_format() -> None:
    """Test that invalid field format is skipped."""
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": "true|User ID",
                        "role_name": "invalid_format",
                    }
                }
            }
        }
    }

    available_fields = get_available_fields(config, "access.subcommands.map")

    assert "user_id" in available_fields
    assert "role_name" not in available_fields


@pytest.mark.unit
def test_get_default_field_names_success() -> None:
    """Test getting default field names returns only 'true' flagged fields."""
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

    default_fields = get_default_field_names(config, "access.subcommands.map")

    assert default_fields == ["user_id", "role_name"]
