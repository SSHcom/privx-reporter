"""Validation functions for CLI-requested fields."""

from typing import Any

from lib._report.fields._helpers import get_fields_section, parse_field_value
from lib._report.fields.config import get_available_fields


def validate_requested_fields(config: dict[str, Any], report_path: str, requested_fields: list[str]) -> None:
    """
    Validate requested fields (from CLI --fields) against configuration.

    Checks:
    - All requested fields exist in configuration
    - None are marked as "redact"
    - No duplicates in request

    Args:
        config: Configuration dictionary (from config.toml)
        report_path: Path to report section (e.g., "access.subcommands.map")
        requested_fields: Field names from CLI --fields option

    Raises:
        ValueError: For invalid, missing, redacted, or duplicate fields
    """
    # Check for duplicate fields
    seen = set()
    duplicates = []
    for field in requested_fields:
        if field in seen:
            duplicates.append(field)
        seen.add(field)

    if duplicates:
        raise ValueError(
            f"Duplicate field(s) in --fields option: {', '.join(duplicates)}\nEach field should be specified only once."
        )

    available_fields = get_available_fields(config, report_path)

    # Check for invalid fields
    invalid_fields = [field for field in requested_fields if field not in available_fields]
    if invalid_fields:
        available_field_names = sorted(available_fields.keys())
        raise ValueError(
            f"Invalid field(s) requested: {', '.join(invalid_fields)}\n"
            f"Available fields: {', '.join(available_field_names)}"
        )

    # Check for redacted fields
    fields = get_fields_section(config, report_path)

    redacted_fields = []
    for field in requested_fields:
        if field in fields:
            field_value = fields[field]
            parsed = parse_field_value(field, field_value)
            if parsed is not None:
                flag, _ = parsed
                if flag == "redact":
                    redacted_fields.append(field)

    if redacted_fields:
        raise ValueError(
            f"Field(s) are redacted and cannot be included: {', '.join(redacted_fields)}\n"
            "Redacted fields are excluded from output for security reasons."
        )
