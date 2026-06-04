"""Tests for output field validation functions."""

import pytest

from lib._report.fields.validation import validate_requested_fields


@pytest.mark.unit
def test_validate_requested_fields_valid() -> None:
    """Test validation with valid requested fields."""
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": "true|User ID",
                        "role_name": "true|Role Name",
                        "target_hosts": "false|Target Hosts",
                    }
                }
            }
        }
    }

    validate_requested_fields(config, "access.subcommands.map", ["user_id", "role_name", "target_hosts"])


@pytest.mark.unit
def test_validate_requested_fields_duplicate() -> None:
    """Test validation raises error for duplicate fields."""
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": "true|User ID",
                        "role_name": "true|Role Name",
                    }
                }
            }
        }
    }

    with pytest.raises(ValueError, match="Duplicate field\\(s\\) in --fields option"):
        validate_requested_fields(config, "access.subcommands.map", ["user_id", "user_id", "role_name"])


@pytest.mark.unit
def test_validate_requested_fields_invalid() -> None:
    """Test validation raises error for invalid field names."""
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": "true|User ID",
                        "role_name": "true|Role Name",
                    }
                }
            }
        }
    }

    with pytest.raises(ValueError, match="Invalid field\\(s\\) requested"):
        validate_requested_fields(config, "access.subcommands.map", ["user_id", "invalid_field"])


@pytest.mark.unit
def test_validate_requested_fields_redacted() -> None:
    """Test validation raises error for redacted fields (shows as invalid since not in available_fields)."""
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": "true|User ID",
                        "email": "redact|Email",
                    }
                }
            }
        }
    }

    # Redacted fields are excluded from available_fields, so they fail invalid check first
    with pytest.raises(ValueError, match="Invalid field\\(s\\) requested"):
        validate_requested_fields(config, "access.subcommands.map", ["user_id", "email"])


@pytest.mark.unit
def test_validate_requested_fields_empty_list() -> None:
    """Test validation with empty list (should pass but be handled by caller)."""
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

    # Empty list should not raise an error (caller should handle this)
    validate_requested_fields(config, "access.subcommands.map", [])


@pytest.mark.unit
def test_validate_requested_fields_missing_config_path() -> None:
    """Test validation raises error when config path is missing."""
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
        validate_requested_fields(config, "access.subcommands.map", ["user_id"])
