"""Field selection and header generation for report output."""

import argparse
from typing import Any

from lib._report.error import ValidationError
from lib._report.fields._helpers import get_fields_section, parse_field_value
from lib._report.fields.config import get_available_fields, get_default_field_names
from lib._report.fields.validation import validate_requested_fields


def get_requested_fields(args: argparse.Namespace, config: dict[str, Any], report_path: str) -> list[str] | None:
    """
    Process --fields CLI option.

    Cases:
    1. No --fields: Returns None (use defaults)
    2. --fields (no value): Prints available fields and exits
    3. --fields value1,value2: Returns validated field list

    Args:
        args: Parsed command line arguments
        config: Configuration dictionary (from config.toml)
        report_path: Path to report section (e.g., "access.subcommands.map")

    Returns:
        None for defaults, or validated field list
        (Exits if --fields without value)

    Raises:
        ValidationError: If --fields value is invalid
    """
    if not hasattr(args, "fields") or args.fields is None:
        return None

    if args.fields == "":
        from lib._report.fields.print import print_available_fields_and_exit

        print_available_fields_and_exit(config, report_path)
        return None

    # Handle special "all" keyword to include all fields
    if args.fields.lower() == "all":
        available_fields = get_available_fields(config, report_path)
        # Return all fields in the order they appear in config
        fields = get_fields_section(config, report_path)
        all_fields = [field_name for field_name in fields.keys() if field_name in available_fields]
        return all_fields

    # Parse comma-separated list
    requested_fields = [f.strip() for f in args.fields.split(",") if f.strip()]

    if not requested_fields:
        raise ValidationError(
            "Invalid --fields option",
            "Provide field names separated by commas, e.g., --fields field1,field2",
        )

    # Expand "*" to all default fields
    if "*" in requested_fields:
        default_fields = get_default_field_names(config, report_path)
        expanded_fields = []
        seen = set()

        for field in requested_fields:
            if field == "*":
                for default_field in default_fields:
                    if default_field not in seen:
                        expanded_fields.append(default_field)
                        seen.add(default_field)
            else:
                if field not in seen:
                    expanded_fields.append(field)
                    seen.add(field)

        requested_fields = expanded_fields

    validate_requested_fields(config, report_path, requested_fields)
    return requested_fields


def get_field_names_and_headers(
    config: dict[str, Any], report_path: str, requested_fields: list[str] | None = None
) -> tuple[list[str], list[str]]:
    """
    Extract field names and headers from output configuration.

    Modes:
    1. Config-based (requested_fields=None): Returns fields marked "true"
    2. CLI-based (requested_fields provided): Returns fields in user-specified order

    Args:
        config: Configuration dictionary (from config.toml)
        report_path: Path to report section (e.g., "access.subcommands.map")
        requested_fields: Optional field list from CLI --fields

    Returns:
        (field_names, header_labels)
        - field_names: Field keys in order
        - header_labels: Human-readable labels from config

    Raises:
        ValueError: If config is invalid or fields are invalid
    """
    fields = get_fields_section(config, report_path)

    # CLI-based selection
    if requested_fields is not None:
        validate_requested_fields(config, report_path, requested_fields)
        available_fields = get_available_fields(config, report_path)

        field_names: list[str] = []
        header_labels: list[str] = []

        for field_name in requested_fields:
            if field_name in available_fields:
                field_names.append(field_name)
                header_labels.append(available_fields[field_name])

        return field_names, header_labels

    # Config-based selection (default)
    field_names = []
    header_labels = []

    for field_key, field_value in fields.items():
        parsed = parse_field_value(field_key, field_value)
        if parsed is None:
            continue

        flag, label = parsed

        if flag == "true":
            field_names.append(field_key)
            header_labels.append(label)

    return field_names, header_labels
