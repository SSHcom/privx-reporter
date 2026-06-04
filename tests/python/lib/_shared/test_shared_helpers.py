"""Tests for lib._shared.helpers."""

import argparse

import pytest

from lib._shared.helpers import add_options


@pytest.mark.unit
def test_add_options_adds_arguments_from_spec() -> None:
    """add_options adds arguments and uses option key as dest by default."""
    parser = argparse.ArgumentParser()
    add_options(
        parser,
        {
            "host": {"flags": ["--host"], "help": "Target host."},
            "port": {"flags": ["-p", "--port"], "required": True, "help": "Port."},
        },
    )
    args = parser.parse_args(["--host", "example.com", "-p", "22"])
    assert args.host == "example.com"
    assert args.port == "22"


@pytest.mark.unit
def test_add_options_skips_non_dict_specs() -> None:
    """add_options skips option values that are not dicts."""
    parser = argparse.ArgumentParser()
    add_options(
        parser,
        {
            "valid": {"flags": ["--valid"], "help": "Valid option."},
            "invalid": True,  # not a dict
        },
    )
    args = parser.parse_args(["--valid", "x"])
    assert args.valid == "x"
    assert not hasattr(args, "invalid")
