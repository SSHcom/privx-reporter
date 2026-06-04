"""Helper functions for fields configuration."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_fields_section(config: dict[str, Any], report_path: str) -> dict[str, Any]:
    """
    Navigate config path and return fields section.

    Args:
        config: Configuration dictionary (from config.toml)
        report_path: Path to report section (e.g., "access.subcommands.map")

    Returns:
        Fields dictionary from configuration

    Raises:
        ValueError: If config section is missing or invalid
    """
    if not config:
        raise ValueError("Configuration dictionary is empty or None")

    try:
        fields_section = config
        for key in report_path.split("."):
            fields_section = fields_section[key]

        if "fields" not in fields_section:
            raise ValueError(f"Missing 'fields' section in {report_path}")

        fields = fields_section["fields"]

        if not fields:
            raise ValueError(f"No fields defined in {report_path}.fields")

        if not isinstance(fields, dict):
            raise ValueError(f"Fields section must be a dictionary, got {type(fields)}")

        return fields

    except KeyError as e:
        raise ValueError(f"Configuration path {report_path} not found: {e}") from e


def parse_field_value(field_key: str, field_value: object) -> tuple[str, str] | None:
    """
    Parse a field value string into flag and label.

    Args:
        field_key: Field key name (for error messages)
        field_value: Field value from config (format: "flag|label")

    Returns:
        (flag, label) if parsing succeeds, None otherwise
        - flag: Field flag (true/false/redact), lowercased and stripped
        - label: Header label, stripped
    """
    if not isinstance(field_value, str):
        logger.warning(f"Invalid field value for {field_key}: expected string, got {type(field_value)}")
        return None

    try:
        flag, label = field_value.split("|", 1)
    except ValueError:
        logger.warning(f"Invalid field format for {field_key}: expected 'flag|label', got '{field_value}'")
        return None

    flag = flag.strip().lower()
    label = label.strip()

    return (flag, label)
