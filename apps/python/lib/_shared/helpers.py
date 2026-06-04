import argparse
from pathlib import Path
from typing import Any, cast


def repo_root(start: Path | None = None) -> Path:
    """Return repository or install root (directory containing pyproject.toml)."""
    current = (start or Path(__file__)).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    msg = "Could not locate repository root (pyproject.toml not found)"
    raise RuntimeError(msg)


def python_app_root(start: Path | None = None) -> Path:
    """Return the Python app root (monorepo ``apps/python/`` or flat install root)."""
    root = repo_root(start)
    dev_root = root / "apps" / "python"
    if dev_root.is_dir():
        return dev_root
    return root


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
