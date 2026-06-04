def normalize_name(name: str) -> str:
    """
    Normalize a report or command name for display.

    - Replace "_" and "-" characters with spaces.
    - Collapse multiple spaces.
    - Capitalize the first letter of the resulting string.
    """
    if not name:
        return ""

    # Replace separators with spaces
    cleaned = name.strip().replace("_", " ").replace("-", " ")

    if not cleaned:
        return ""

    # Collapse multiple spaces between words
    cleaned = " ".join(cleaned.split())

    return cleaned[0].upper() + cleaned[1:]
