"""Print available fields for a report and exit."""

import logging
import sys
from typing import Any

from lib._report.error import ConfigError
from lib._report.fields._helpers import get_fields_section, parse_field_value
from lib._report.fields.config import get_available_fields

logger = logging.getLogger(__name__)


def print_available_fields_and_exit(config: dict[str, Any], report_path: str) -> None:
    """
    Print available fields for a report and exit.

    Args:
        config: Configuration dictionary (from config.toml)
        report_path: Path to report section (e.g., "access.subcommands.map")

    Raises:
        ConfigError: If no fields found or configuration invalid
    """
    available_fields = get_available_fields(config, report_path)

    if not available_fields:
        raise ConfigError("No available fields found", f"Check configuration at {report_path}")

    # Get fields section to show which are in default output
    fields = get_fields_section(config, report_path)

    # Separate default (true) and optional (false) fields
    default_fields = []
    optional_fields = []

    for field_name, header_label in sorted(available_fields.items()):
        field_value = fields.get(field_name, "")
        parsed = parse_field_value(field_name, field_value)
        if parsed is not None:
            flag, _ = parsed
            if flag == "true":
                default_fields.append((field_name, header_label))
            else:
                optional_fields.append((field_name, header_label))

    if default_fields:
        print("Default fields (included by default):")
        for field_name, header_label in default_fields:
            print(f"  {field_name:20s} - {header_label}")
        print()

    if optional_fields:
        print("Optional fields (use --fields to include):")
        for field_name, header_label in optional_fields:
            print(f"  {field_name:20s} - {header_label}")
        print()

    print("Usage examples:")
    # Format report path for command (e.g., "access.subcommands.map" -> "access map")
    cmd_path = report_path.replace(".subcommands.", " ")
    print(f"  ./report {cmd_path} --fields all  # Include all fields")
    if default_fields:
        example_fields = ",".join([f[0] for f in default_fields[:3]])
        print(f"  ./report {cmd_path} --fields {example_fields}")
    if optional_fields and default_fields:
        print(f"  ./report {cmd_path} --fields {default_fields[0][0]},{optional_fields[0][0]}")
    if optional_fields:
        print(f"  ./report {cmd_path} --fields *,{optional_fields[0][0]}  # All defaults + optional")

    sys.exit(0)
