"""Tests for admin CLI parser."""

import pytest

from lib._admin.cli_parser import build_parser


def _args_spec() -> dict[str, object]:
    return {
        "event": {
            "help": "Manage event administration actions.",
            "description": """\
Manage event administration actions.

Subcommands:
  enable   Enable an event code
  disable  Disable an event code
""",
            "subcommands": {
                "enable": {
                    "help": "Enable an event code.",
                    "options": {
                        "code": {
                            "flags": ["--code"],
                            "required": True,
                            "help": "Event code to enable.",
                        }
                    },
                },
                "disable": {
                    "help": "Disable an event code.",
                    "options": {
                        "code": {
                            "flags": ["--code"],
                            "required": True,
                            "help": "Event code to disable.",
                        }
                    },
                },
                "list": {
                    "help": "List available events.",
                },
            },
        }
    }


@pytest.mark.unit
def test_build_parser_raises_when_command_missing_description() -> None:
    """build_parser raises ValueError if a command has no description."""
    spec = {"event": {"help": "Event actions."}}  # no description

    with pytest.raises(ValueError, match="Command 'event' is missing a required description"):
        build_parser(spec)


@pytest.mark.unit
def test_build_parser_requires_code_for_enable() -> None:
    """Enable subcommand requires --code."""
    parser = build_parser(_args_spec())

    with pytest.raises(SystemExit):
        parser.parse_args(["event", "enable"])


@pytest.mark.unit
def test_build_parser_parses_disable_code() -> None:
    """Disable subcommand parses --code value."""
    parser = build_parser(_args_spec())
    args = parser.parse_args(["event", "disable", "--code", "AUDIT_001"])

    assert args.command == "event"
    assert args.subcommand == "disable"
    assert args.code == "AUDIT_001"


@pytest.mark.unit
def test_group_help_preserves_multiline_description(capsys: pytest.CaptureFixture[str]) -> None:
    """Group help keeps multiline description from group config."""
    parser = build_parser(_args_spec())

    with pytest.raises(SystemExit):
        parser.parse_args(["event", "-h"])

    out = capsys.readouterr().out
    assert "Manage event administration actions.\n\nSubcommands:" in out


@pytest.mark.unit
def test_subcommand_help_has_no_report_output_options(capsys: pytest.CaptureFixture[str]) -> None:
    """Admin subcommand help excludes report-specific output options."""
    parser = build_parser(_args_spec())

    with pytest.raises(SystemExit):
        parser.parse_args(["event", "enable", "-h"])

    out = capsys.readouterr().out
    assert "--fields" not in out
    assert "--to-json" not in out
    assert "--to-stdout" not in out
    assert "--output-dir" not in out


@pytest.mark.unit
def test_build_parser_parses_list_without_code() -> None:
    """List subcommand should not require --code."""
    parser = build_parser(_args_spec())
    args = parser.parse_args(["event", "list"])

    assert args.command == "event"
    assert args.subcommand == "list"
