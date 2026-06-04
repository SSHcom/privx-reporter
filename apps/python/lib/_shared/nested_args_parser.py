import argparse
import sys
from typing import Never


class NestedArgumentParser(argparse.ArgumentParser):
    """Argument parser that routes unrecognized argument errors to the active subcommand."""

    def _resolve_active_parser(self) -> argparse.ArgumentParser:
        parser: argparse.ArgumentParser = self
        args: list[str] = sys.argv[1:]
        idx = 0

        while idx < len(args):
            token = args[idx]
            if token.startswith("-"):
                break

            subparsers_action = next(
                (action for action in parser._actions if isinstance(action, argparse._SubParsersAction)),
                None,
            )
            if subparsers_action is None:
                break

            next_parser = subparsers_action.choices.get(token)
            if next_parser is None:
                break

            parser = next_parser
            idx += 1

        return parser

    def error(self, message: str) -> Never:
        if "unrecognized arguments:" in message:
            active_parser = self._resolve_active_parser()
            if active_parser is not self:
                active_parser.print_usage(sys.stderr)
                active_parser.exit(2, f"{active_parser.prog}: error: {message}\n")

        super().error(message)
