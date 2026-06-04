"""Tests for NestedArgumentParser error routing."""

import pytest

from lib._shared import NestedArgumentParser


@pytest.mark.unit
def test_unrecognized_args_error_reported_at_subcommand_exit_2() -> None:
    """Unknown arguments trigger exit(2) and are routed to the active subcommand."""
    parser = NestedArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd", required=True, parser_class=NestedArgumentParser)
    subparsers.add_parser("sub", help="A subcommand.")

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["sub", "--unknown", "x"])
    assert exc_info.value.code == 2
