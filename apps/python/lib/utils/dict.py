"""List validation utilities.

This module provides validation functions for lists and dictionaries.
"""

from typing import Any


def validate_dict_contains(data: dict[str, Any], required: list[str]) -> None:
    """
    Validate that a data dictionary contains all required fields.

    Args:
        data: Dictionary containing data
        required: List of required field names

    Raises:
        ValueError: If data is missing any required fields
    """
    missing_fields = [field for field in required if field not in data]

    if missing_fields:
        raise ValueError(f"Data dictionary is missing required fields: {missing_fields}")
