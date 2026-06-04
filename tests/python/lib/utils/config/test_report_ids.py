"""Tests for report_ids utility functions."""

import pytest

from lib.utils.config.report_ids import make_report_ids


@pytest.mark.unit
def test_make_report_ids_basic() -> None:
    """Test that make_report_ids creates correct identifiers from command and subcommand."""
    result = make_report_ids("access", "host-map")

    assert result.command == "access"
    assert result.sub_command == "host-map"
    assert result.report_prefix == "access.host-map"
    assert result.config_key == "access.subcommands.host-map"


@pytest.mark.unit
def test_make_report_ids_roles_command() -> None:
    """Test make_report_ids with roles command."""
    result = make_report_ids("roles", "list")

    assert result.command == "roles"
    assert result.sub_command == "list"
    assert result.report_prefix == "roles.list"
    assert result.config_key == "roles.subcommands.list"


@pytest.mark.unit
def test_make_report_ids_connections_command() -> None:
    """Test make_report_ids with connections command."""
    result = make_report_ids("connections", "search")

    assert result.command == "connections"
    assert result.sub_command == "search"
    assert result.report_prefix == "connections.search"
    assert result.config_key == "connections.subcommands.search"


@pytest.mark.unit
def test_make_report_ids_with_underscore_subcommand() -> None:
    """Test make_report_ids correctly handles subcommand with underscores."""
    result = make_report_ids("access", "account_restrictions")

    assert result.command == "access"
    assert result.sub_command == "account_restrictions"
    assert result.report_prefix == "access.account_restrictions"
    assert result.config_key == "access.subcommands.account_restrictions"


@pytest.mark.unit
def test_make_report_ids_return_has_all_keys() -> None:
    """Test that make_report_ids returns a ReportIds with all required attributes."""
    result = make_report_ids("test", "subtest")

    assert hasattr(result, "command")
    assert hasattr(result, "sub_command")
    assert hasattr(result, "report_prefix")
    assert hasattr(result, "config_key")


@pytest.mark.unit
def test_make_report_ids_with_single_word_command() -> None:
    """Test make_report_ids with single word command and subcommand."""
    result = make_report_ids("users", "all")

    assert result.command == "users"
    assert result.sub_command == "all"
    assert result.report_prefix == "users.all"
    assert result.config_key == "users.subcommands.all"


@pytest.mark.unit
def test_make_report_ids_prefix_format() -> None:
    """Test that report_prefix uses dot separator."""
    result = make_report_ids("cmd", "subcmd")

    assert "." in result.report_prefix
    assert result.report_prefix == "cmd.subcmd"


@pytest.mark.unit
def test_make_report_ids_config_key_format() -> None:
    """Test that config_key uses dot separator and includes 'subcommands'."""
    result = make_report_ids("cmd", "subcmd")

    assert "." in result.config_key
    assert "subcommands" in result.config_key
    assert result.config_key == "cmd.subcommands.subcmd"


@pytest.mark.unit
def test_make_report_ids_with_multiple_hyphens() -> None:
    """Test make_report_ids with commands/subcommands containing multiple hyphens."""
    result = make_report_ids("access-control", "host-user-map")

    assert result.command == "access-control"
    assert result.sub_command == "host-user-map"
    assert result.report_prefix == "access-control.host-user-map"
    assert result.config_key == "access-control.subcommands.host-user-map"
