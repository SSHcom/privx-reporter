"""String utility functions."""

import re


def sanitize_string(value: str) -> str:
    """
    Sanitize a string to be safe for use in file names or identifiers.

    The sanitization rules are:
    - Convert to lowercase
    - Replace spaces and underscores with hyphens
    - Replace any non-alphanumeric character (except hyphen) with hyphen
    - Collapse consecutive hyphens into a single hyphen
    - Strip leading and trailing hyphens
    """
    # Normalize to string and lowercase
    sanitized = str(value).lower()

    # Replace spaces and underscores with hyphens
    sanitized = sanitized.replace(" ", "-").replace("_", "-")

    # Replace any character that isn't alphanumeric or hyphen with hyphen
    sanitized = re.sub(r"[^a-z0-9-]", "-", sanitized)

    # Collapse multiple hyphens into one
    sanitized = re.sub(r"-{2,}", "-", sanitized)

    # Strip leading/trailing hyphens
    sanitized = sanitized.strip("-")

    return sanitized


def to_ui_message(message: str | None) -> str | None:
    """
    Convert CLI-style option names to UI-friendly format.

    Replaces:
    - ``--<name>`` with ``"<name>"``
    - ``--<name>-<name>`` with ``"<name> <name>"``
    - Supports up to 4 elements (e.g., ``--access-group-comment`` -> ``"access group comment"``)
    """
    if message is None:
        return None

    def replace_option(match: re.Match) -> str:
        option = match.group(0)
        without_prefix = option[2:]
        parts = without_prefix.split("-")
        return '"' + " ".join(parts) + '"'

    return re.sub(r"--([a-zA-Z][a-zA-Z0-9]*(?:-[a-zA-Z][a-zA-Z0-9]*){0,3})", replace_option, message)
