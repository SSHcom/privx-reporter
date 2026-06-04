from typing import Any

from lib._shared import (
    CommandWithDescriptionFormatter,
    CommandWithoutDescriptionFormatter,
    NestedArgumentParser,
    RawTextHelpFormatter,
    add_options,
)


def build_parser(spec: dict[str, Any]) -> NestedArgumentParser:
    """Build the admin CLI parser from a spec dictionary.

    Constructs a two-level command hierarchy:
    - top-level commands (args.command)
    - optional subcommands (args.subcommand)

    When running a command, CLI arguments are parsed according to the command specification
    and help or error messages are displayed accordingly.
    """
    parser = NestedArgumentParser(prog="admin", formatter_class=CommandWithoutDescriptionFormatter)
    # Create command_parsers group
    command_parsers = parser.add_subparsers(dest="command", required=True, parser_class=NestedArgumentParser)

    # Loop over top-level commands
    for command_name, command_spec in spec.items():
        if not command_spec.get("description"):
            raise ValueError(f"Command '{command_name}' is missing a required description.")

        # Add command parser to the top-level command_parsers
        command_parser = command_parsers.add_parser(
            command_name,
            help=command_spec.get("help"),
            description=command_spec.get("description"),
            formatter_class=CommandWithDescriptionFormatter,
        )

        if "subcommands" in command_spec:
            # Create subcommand_parsers group and add group to the command_parser
            subcommand_parsers = command_parser.add_subparsers(
                dest="subcommand", required=True, parser_class=NestedArgumentParser
            )

            # Loop over sub commands
            for subcommand_name, subcommand_spec in command_spec["subcommands"].items():
                # Create subcommand parser and add parser to subcommand_parsers
                subcommand_parser = subcommand_parsers.add_parser(
                    subcommand_name,
                    help=subcommand_spec.get("help"),
                    description=subcommand_spec.get("help"),
                    formatter_class=RawTextHelpFormatter,
                )
                options = subcommand_spec.get("options", {})
                if isinstance(options, dict):
                    add_options(subcommand_parser, options)
        else:
            options = command_spec.get("options", {})
            if isinstance(options, dict):
                add_options(command_parser, options)

    return parser
