import argparse
from typing import Any, cast


def add_options(parser: argparse.ArgumentParser, options: dict[str, Any]) -> None:
    """Add arguments to a parser from a spec dictionary.

    Args:
        parser: The argument parser to add options to.
        options: Dictionary mapping option names to their specs. Each spec
            should contain 'flags' (list of flag strings), and optionally
            'required', 'help', 'dest', and 'action'.
    """
    for option_name, option_spec in options.items():
        if not isinstance(option_spec, dict):
            continue

        kwargs: dict[str, Any] = {
            "required": option_spec.get("required", False),
            "help": option_spec.get("help"),
            "dest": option_spec.get("dest", option_name),
        }

        if "action" in option_spec:
            kwargs["action"] = option_spec["action"]

        flags = cast("list[str]", option_spec["flags"])
        parser.add_argument(*flags, **kwargs)
