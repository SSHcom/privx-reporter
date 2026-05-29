"""Tests for CLI parser option destination mapping and helpers."""

import pytest

from lib._report.cli_parser import (
    _build_fields_help_text,
    _get_output_flag_config,
    build_parser,
)


@pytest.mark.unit
def test_get_output_flag_config_list_returns_to_file() -> None:
    """List command uses --to-file flag."""
    assert _get_output_flag_config("list") == {
        "flag": "--to-file",
        "help": "Write results to a file instead of stdout.",
    }


@pytest.mark.unit
def test_get_output_flag_config_non_list_returns_to_stdout() -> None:
    """Non-list commands use --to-stdout flag."""
    assert _get_output_flag_config("access") == {
        "flag": "--to-stdout",
        "help": "Output results to stdout instead of writing to a file.",
    }


@pytest.mark.unit
def test_build_fields_help_text_without_fields_in_spec() -> None:
    """Returns base --fields help when spec has no 'fields' key."""
    text = _build_fields_help_text({"help": "List something."})
    assert "Override field selection." in text
    assert "--fields" in text
    assert "List available fields" in text


@pytest.mark.unit
def test_build_fields_help_text_with_fields_in_spec() -> None:
    """Returns help text when spec has 'fields' key (default/optional not yet rendered)."""
    text = _build_fields_help_text({"fields": {"foo": "true|x", "bar": "false|y"}})
    assert "Override field selection." in text
    assert "List available fields" in text


@pytest.mark.unit
def test_build_parser_uses_option_key_as_dest_for_subcommands() -> None:
    """Option key should map to argparse dest for subcommands."""
    spec = {
        "connections": {
            "subcommands": {
                "query": {
                    "help": "Query connections.",
                    "options": {
                        "target_host_address": {
                            "flags": ["--host-address"],
                            "required": False,
                            "help": "Target host address filter.",
                        }
                    },
                }
            }
        }
    }

    parser = build_parser(spec)
    args = parser.parse_args(["connections", "query", "--host-address", "172.31.14.213"])

    assert args.target_host_address == "172.31.14.213"
    assert not hasattr(args, "host_address")


@pytest.mark.unit
def test_build_parser_uses_option_key_as_dest_without_subcommands() -> None:
    """Option key should map to argparse dest for top-level commands."""
    spec = {
        "connections": {
            "help": "Connections report.",
            "options": {
                "target_host_address": {
                    "flags": ["--host-address"],
                    "required": False,
                    "help": "Target host address filter.",
                }
            },
        }
    }

    parser = build_parser(spec)
    args = parser.parse_args(["connections", "--host-address", "172.31.14.213"])

    assert args.target_host_address == "172.31.14.213"
    assert not hasattr(args, "host_address")
