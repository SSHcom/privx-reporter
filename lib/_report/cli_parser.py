import argparse
import sys
from typing import Any

from lib._shared import (
    CommandWithDescriptionFormatter,
    CommandWithoutDescriptionFormatter,
    NestedArgumentParser,
    RawTextHelpFormatter,
    add_options,
)

### FIELDS HELP TEXT ###


def _build_fields_help_text(subcmd_spec: dict[str, Any]) -> str:
    """Build help text for the --fields option from subcommand spec."""
    lines = [
        "Override field selection.",
        "  --fields                  : List available fields",
        "  --fields field1,field2    : Select specific fields",
        "  --fields * [,<field>,...] : Include all default fields",
    ]
    return "\n".join(lines)


### OUTPUT FLAGS CONFIG ###


def _get_output_flag_config(cmd_name: str) -> dict[str, str]:
    """Get output flag configuration based on command type.

    Args:
        cmd_name: The command name (e.g., "list", "access", "connections")

    Returns:
        Dictionary with 'flag' and 'help' keys for the output flag configuration
    """
    if cmd_name == "list":
        return {
            "flag": "--to-file",
            "help": "Write results to a file instead of stdout.",
        }
    return {
        "flag": "--to-stdout",
        "help": "Output results to stdout instead of writing to a file.",
    }


def _add_subcommand_arguments(
    subcmd: argparse.ArgumentParser,
    cmd_name: str,
    subcmd_spec: dict[str, Any],
) -> None:
    """Add --fields, --to-json, output flag, --output-dir, and options to a subcommand parser."""
    subcmd.add_argument(
        "--fields",
        nargs="?",
        const="",
        help=_build_fields_help_text(subcmd_spec),
    )

    subcmd.add_argument(
        "--to-json",
        action="store_true",
        # Presence flag: False by default, True when provided.
        help="Output results as JSON instead of CSV.",
    )

    output_config = _get_output_flag_config(cmd_name)
    subcmd.add_argument(
        output_config["flag"],
        action="store_true",
        # Presence flag: False by default, True when provided.
        help=output_config["help"],
    )

    subcmd.add_argument(
        "--output-dir",
        help="Override the output directory for report files (default: REPORT_OUT_DIR env var).",
    )

    has_fields_flag = "--fields" in sys.argv
    options = subcmd_spec.get("options", {})

    if not isinstance(options, dict):
        return

    normalized_options: dict[str, Any] = {}
    for opt_name, opt in options.items():
        if not isinstance(opt, dict):
            continue
        opt_copy: dict[str, Any] = dict(opt)
        if has_fields_flag:
            opt_copy["required"] = bool(opt.get("required", False)) and not has_fields_flag
        normalized_options[opt_name] = opt_copy

    add_options(subcmd, normalized_options)


### MAIN FUNCTION ###


def build_parser(spec: dict[str, Any]) -> argparse.ArgumentParser:
    """Build the report CLI parser from a spec dictionary.

    Constructs a two-level command hierarchy:
    - top-level commands (args.command)
    - optional subcommands (args.subcommand)

    When running a command, CLI arguments are parsed according to the command specification
    and help or error messages are displayed accordingly.
    """
    parser = NestedArgumentParser(formatter_class=CommandWithoutDescriptionFormatter)
    # Create command_parsers group
    command_parsers = parser.add_subparsers(dest="command", required=True, parser_class=NestedArgumentParser)

    # Loop over top-level commands
    for cmd_name, cmd_spec in spec.items():
        # Add command parser to the top-level command_parsers
        formatter = (
            CommandWithDescriptionFormatter if cmd_spec.get("description") else CommandWithoutDescriptionFormatter
        )
        cmd = command_parsers.add_parser(
            cmd_name,
            help=cmd_spec.get("help"),
            description=cmd_spec.get("description"),
            formatter_class=formatter,
        )

        if "subcommands" in cmd_spec:
            # Create subcommand_parsers group and add group to the command_parser
            subcommand_parsers = cmd.add_subparsers(dest="subcommand", required=True, parser_class=NestedArgumentParser)

            # Loop over subcommands
            for subcmd_name, subcmd_spec in cmd_spec["subcommands"].items():
                # Create subcommand parser and add parser to subcommand_parsers
                subcmd = subcommand_parsers.add_parser(
                    subcmd_name,
                    help=subcmd_spec.get("help"),
                    description=subcmd_spec.get("help"),
                    formatter_class=RawTextHelpFormatter,
                )
                _add_subcommand_arguments(subcmd, cmd_name, subcmd_spec)
        else:
            # No subcommands: add options directly to the command
            options = cmd_spec.get("options", {})
            if isinstance(options, dict):
                filtered_options: dict[str, Any] = {
                    name: spec for name, spec in options.items() if isinstance(spec, dict)
                }
                add_options(cmd, filtered_options)

    return parser
