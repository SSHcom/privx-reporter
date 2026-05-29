"""Configuration reading and parsing for output fields."""

from typing import Any

from lib._report.fields._helpers import get_fields_section, parse_field_value


def get_available_fields(config: dict[str, Any], report_path: str) -> dict[str, str]:
    """
    Get all available fields (excluding redacted) from configuration.

    Args:
        config: Configuration dictionary (from config.toml)
        report_path: Path to report section (e.g., "access.subcommands.map")

    Returns:
        Mapping of field names to header labels
    """
    fields = get_fields_section(config, report_path)

    available_fields: dict[str, str] = {}

    for field_key, field_value in fields.items():
        parsed = parse_field_value(field_key, field_value)
        if parsed is None:
            continue

        flag, label = parsed

        if flag != "redact":
            available_fields[field_key] = label

    return available_fields


def get_default_field_names(config: dict[str, Any], report_path: str) -> list[str]:
    """
    Extract default field names from configuration.

    Default fields are those marked with "true".

    Args:
        config: Configuration dictionary (from config.toml)
        report_path: Path to report section (e.g., "access.subcommands.map")

    Returns:
        List of default field names in configuration order
    """
    fields = get_fields_section(config, report_path)
    default_fields = []

    for field_key, field_value in fields.items():
        parsed = parse_field_value(field_key, field_value)
        if parsed is None:
            continue

        flag, label = parsed

        if flag == "true":
            default_fields.append(field_key)

    return default_fields
