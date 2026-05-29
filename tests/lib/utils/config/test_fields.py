"""Tests for field configuration."""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from lib.utils.config.fields import get_field_names_and_headers, get_requested_fields


@pytest.mark.unit
def test_get_requested_fields_no_fields() -> None:
    """Test that None is returned when --fields option is not provided."""
    args = argparse.Namespace()
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

    result = get_requested_fields(args, config, "access.subcommands.map")

    assert result is None


@pytest.mark.unit
def test_get_requested_fields_none_value() -> None:
    """Test that None is returned when fields is None."""
    args = argparse.Namespace(fields=None)
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

    result = get_requested_fields(args, config, "access.subcommands.map")

    assert result is None


@pytest.mark.unit
@patch("lib._report.fields.print.print_available_fields_and_exit")
@patch("sys.exit")
def test_get_requested_fields_empty_string(mock_exit: MagicMock, mock_list_fields: MagicMock) -> None:
    """Test that empty string triggers print_available_fields_and_exit."""
    args = argparse.Namespace(fields="")
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

    get_requested_fields(args, config, "access.subcommands.map")

    mock_list_fields.assert_called_once_with(config, "access.subcommands.map")


@pytest.mark.unit
def test_get_requested_fields_valid_fields() -> None:
    """Test that valid fields are parsed and returned."""
    args = argparse.Namespace(fields="user_id,role_name")
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": "true|User ID",
                        "role_name": "true|Role Name",
                        "target_hosts": "true|Target Hosts",
                    }
                }
            }
        }
    }

    result = get_requested_fields(args, config, "access.subcommands.map")

    assert result == ["user_id", "role_name"]


@pytest.mark.unit
def test_get_requested_fields_with_whitespace() -> None:
    """Test that whitespace in field list is stripped."""
    args = argparse.Namespace(fields=" user_id , role_name , target_hosts ")
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": "true|User ID",
                        "role_name": "true|Role Name",
                        "target_hosts": "true|Target Hosts",
                    }
                }
            }
        }
    }

    result = get_requested_fields(args, config, "access.subcommands.map")

    assert result == ["user_id", "role_name", "target_hosts"]


@pytest.mark.unit
def test_get_requested_fields_with_false_fields() -> None:
    """Test that false fields can be requested via CLI."""
    args = argparse.Namespace(fields="user_id,target_hosts")
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": "true|User ID",
                        "target_hosts": "false|Target Hosts",
                    }
                }
            }
        }
    }

    result = get_requested_fields(args, config, "access.subcommands.map")

    assert result == ["user_id", "target_hosts"]


@pytest.mark.unit
def test_get_requested_fields_empty_after_parsing() -> None:
    """Test that empty list after parsing raises ValidationError."""
    from lib._report.error import ValidationError

    args = argparse.Namespace(fields="  ,  ,  ")
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

    with pytest.raises(ValidationError, match="Invalid --fields option"):
        get_requested_fields(args, config, "access.subcommands.map")


@pytest.mark.unit
def test_get_requested_fields_invalid_field() -> None:
    """Test that invalid field raises ValueError."""
    args = argparse.Namespace(fields="user_id,invalid_field")
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

    with pytest.raises(ValueError, match="Invalid field\\(s\\) requested"):
        get_requested_fields(args, config, "access.subcommands.map")


@pytest.mark.unit
def test_get_requested_fields_redacted_field() -> None:
    """Test that redacted field raises ValueError (shows as invalid since not in available_fields)."""
    args = argparse.Namespace(fields="user_id,email")
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
        get_requested_fields(args, config, "access.subcommands.map")


@pytest.mark.unit
def test_get_requested_fields_duplicate_fields() -> None:
    """Test that duplicate fields raise ValueError."""
    args = argparse.Namespace(fields="user_id,user_id,role_name")
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
        get_requested_fields(args, config, "access.subcommands.map")


@pytest.mark.unit
def test_get_field_names_and_headers_success() -> None:
    """Test field extraction with true flags and label parsing."""
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": "true|User ID",
                        "role_name": "true|Role Name",
                        "target_hosts": "true|Target Hosts",
                        "target_accounts": "true|Target Accounts",
                    }
                }
            }
        }
    }

    field_names, header_labels = get_field_names_and_headers(config, "access.subcommands.map")

    assert field_names == ["user_id", "role_name", "target_hosts", "target_accounts"]
    assert header_labels == ["User ID", "Role Name", "Target Hosts", "Target Accounts"]


@pytest.mark.unit
def test_get_field_names_and_headers_with_false_flag() -> None:
    """Test that fields with false flag are excluded."""
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": "true|User ID",
                        "role_name": "false|Role Name",
                        "target_hosts": "true|Target Hosts",
                    }
                }
            }
        }
    }

    field_names, header_labels = get_field_names_and_headers(config, "access.subcommands.map")

    assert field_names == ["user_id", "target_hosts"]
    assert header_labels == ["User ID", "Target Hosts"]


@pytest.mark.unit
def test_get_field_names_and_headers_with_redact_flag() -> None:
    """Test that fields with redact flag are excluded."""
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": "true|User ID",
                        "email": "redact|Email",
                        "role_name": "true|Role Name",
                    }
                }
            }
        }
    }

    field_names, header_labels = get_field_names_and_headers(config, "access.subcommands.map")

    assert field_names == ["user_id", "role_name"]
    assert header_labels == ["User ID", "Role Name"]


@pytest.mark.unit
def test_get_field_names_and_headers_with_whitespace() -> None:
    """Test that whitespace is properly stripped from flags and labels."""
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": " true | User ID ",
                        "role_name": "  true  |  Role Name  ",
                    }
                }
            }
        }
    }

    field_names, header_labels = get_field_names_and_headers(config, "access.subcommands.map")

    assert field_names == ["user_id", "role_name"]
    assert header_labels == ["User ID", "Role Name"]


@pytest.mark.unit
def test_get_field_names_and_headers_empty_config() -> None:
    """Test that empty config raises ValueError."""
    with pytest.raises(ValueError, match="Configuration dictionary is empty or None"):
        get_field_names_and_headers({}, "access.subcommands.map")


@pytest.mark.unit
def test_get_field_names_and_headers_missing_path() -> None:
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
        get_field_names_and_headers(config, "access.subcommands.map")


@pytest.mark.unit
def test_get_field_names_and_headers_missing_fields_section() -> None:
    """Test that missing fields section raises ValueError."""
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "help": "Some help text",
                }
            }
        }
    }

    with pytest.raises(ValueError, match="Missing 'fields' section in access.subcommands.map"):
        get_field_names_and_headers(config, "access.subcommands.map")


@pytest.mark.unit
def test_get_field_names_and_headers_empty_fields() -> None:
    """Test that empty fields dictionary raises ValueError."""
    config = {"access": {"subcommands": {"map": {"fields": {}}}}}

    with pytest.raises(ValueError, match="No fields defined in access.subcommands.map.fields"):
        get_field_names_and_headers(config, "access.subcommands.map")


@pytest.mark.unit
def test_get_field_names_and_headers_invalid_field_format() -> None:
    """Test that invalid field format (no pipe) is skipped with warning."""
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": "true|User ID",
                        "role_name": "invalid_format",
                        "target_hosts": "true|Target Hosts",
                    }
                }
            }
        }
    }

    field_names, header_labels = get_field_names_and_headers(config, "access.subcommands.map")

    assert field_names == ["user_id", "target_hosts"]
    assert header_labels == ["User ID", "Target Hosts"]


@pytest.mark.unit
def test_get_field_names_and_headers_with_requested_fields() -> None:
    """Test field extraction with requested_fields parameter (CLI mode)."""
    config = {
        "access": {
            "subcommands": {
                "map": {
                    "fields": {
                        "user_id": "true|User ID",
                        "role_name": "true|Role Name",
                        "target_hosts": "true|Target Hosts",
                        "target_accounts": "false|Target Accounts",
                    }
                }
            }
        }
    }

    # Request fields in different order, including a false field
    requested_fields = ["target_accounts", "user_id", "target_hosts"]
    field_names, header_labels = get_field_names_and_headers(
        config, "access.subcommands.map", requested_fields=requested_fields
    )

    # Should return in requested order
    assert field_names == ["target_accounts", "user_id", "target_hosts"]
    assert header_labels == ["Target Accounts", "User ID", "Target Hosts"]


@pytest.mark.unit
def test_get_field_names_and_headers_with_invalid_requested_field() -> None:
    """Test that invalid requested field raises ValueError."""
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
        get_field_names_and_headers(config, "access.subcommands.map", requested_fields=["user_id", "invalid_field"])


@pytest.mark.unit
def test_get_field_names_and_headers_with_redacted_requested_field() -> None:
    """Test that requesting a redacted field raises ValueError (shows as invalid since not in available_fields)."""
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
        get_field_names_and_headers(config, "access.subcommands.map", requested_fields=["user_id", "email"])
