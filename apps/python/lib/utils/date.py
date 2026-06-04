"""Timestamp parsing utilities."""

import re
from datetime import date, datetime, timedelta

from lib._report.error import ValidationError

# Regex to match fractional seconds before timezone
_FRACTION_RE = re.compile(r"(\.\d+)(?=[+-]\d{2}:\d{2}$)")


def parse_iso_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO 8601 timestamp string, handling variable-length microseconds.

    Python's fromisoformat() requires exactly 6 digits for microseconds,
    but some APIs return fewer digits. This method normalizes the format.

    Args:
        timestamp_str: ISO 8601 timestamp string (e.g., '2025-12-29T07:30:44.04528+00:00')

    Returns:
        datetime object with timezone info

    Raises:
        ValueError: If the timestamp string is invalid

    Examples:
        >>> parse_iso_timestamp('2025-12-29T07:30:44.04528+00:00')
        datetime.datetime(2025, 12, 29, 7, 30, 44, 45280, tzinfo=datetime.timezone.utc)

        >>> parse_iso_timestamp('2025-12-29T07:30:44.1Z')
        datetime.datetime(2025, 12, 29, 7, 30, 44, 100000, tzinfo=datetime.timezone.utc)

        >>> parse_iso_timestamp('2025-12-29T07:30:44Z')
        datetime.datetime(2025, 12, 29, 7, 30, 44, tzinfo=datetime.timezone.utc)
    """
    # Replace 'Z' with '+00:00' for UTC
    timestamp_str = timestamp_str.replace("Z", "+00:00")

    # Normalize fractional seconds to exactly 6 digits
    def fix(match: re.Match[str]) -> str:
        frac = match.group(1)[1:]  # strip dot
        frac = (frac + "000000")[:6]  # pad to 6 digits, truncate if longer
        return "." + frac

    timestamp_str = _FRACTION_RE.sub(fix, timestamp_str)
    return datetime.fromisoformat(timestamp_str)


def format_iso_timestamp(dt: datetime) -> str:
    """Format datetime object to ISO 8601 string with 'Z' suffix for UTC.

    Formats a timezone-aware datetime to ISO 8601 format, replacing '+00:00'
    with 'Z' for UTC timezone.

    Args:
        dt: datetime object (should be timezone-aware)

    Returns:
        ISO 8601 formatted string with 'Z' suffix for UTC (e.g., '2025-01-09T12:00:00Z')

    Examples:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2025, 1, 9, 12, 0, 0, tzinfo=timezone.utc)
        >>> format_iso_timestamp(dt)
        '2025-01-09T12:00:00Z'
    """
    return dt.isoformat().replace("+00:00", "Z")


def validate_date(date_str: str | date | datetime, param_name: str, end_of_day: bool = False) -> str:
    """Validate date string or date/datetime object and return it in ISO format.

    If the date is in YYYY-MM-DD format (or a date/datetime object), converts it to ISO format with time set
    to either start of day (00:00:00.000000Z) or end of day (23:59:59.999999Z).
    Otherwise, validates the date string and returns it as-is if valid.

    Args:
        date_str: Date string to validate (YYYY-MM-DD or ISO format) or date/datetime object
        param_name: Name of the parameter (for error messages)
        end_of_day: If True, converts YYYY-MM-DD to end of day (23:59:59.999999Z),
                    otherwise to start of day (00:00:00.000000Z). Default is False.

    Returns:
        Validated date string (ISO format if input was YYYY-MM-DD, otherwise original)

    Raises:
        SystemExit: If the date format is invalid

    Examples:
        >>> validate_date('2026-01-01', 'from_date')
        '2026-01-01T00:00:00.000000Z'

        >>> validate_date('2026-01-01', 'to_date', end_of_day=True)
        '2026-01-01T23:59:59.999999Z'

        >>> validate_date('2026-01-01T12:34:56Z', 'from_date')
        '2026-01-01T12:34:56Z'
    """
    # Handle date or datetime objects (e.g., from Streamlit date_input)
    if isinstance(date_str, (date, datetime)):
        # Convert date/datetime to YYYY-MM-DD string format
        date_str = date_str.strftime("%Y-%m-%d")

    # First, try to parse as YYYY-MM-DD format
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        # Convert to ISO format with start or end of day
        if end_of_day:
            return dt.strftime("%Y-%m-%dT23:59:59.999999") + "Z"
        else:
            return dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    except ValueError:
        pass

    # Otherwise, validate the date string as-is (assuming ISO format)
    try:
        parse_iso_timestamp(date_str)
        return date_str
    except ValueError:
        raise ValidationError(
            f"Invalid {param_name} format: '{date_str}'. "
            "Expected YYYY-MM-DD or ISO format (e.g., 2025-01-15 or 2025-01-15T00:00:00Z)",
            "connections list --from YYYY-MM-DD --to YYYY-MM-DD",
        )


def get_date_range(days: int) -> tuple[str, str]:
    """Get date range as YYYY-MM-DD strings from N days ago to today.

    Args:
        days: Number of days in the past (e.g., 7 = last 7 days)

    Returns:
        Tuple of (from_date, to_date) in YYYY-MM-DD format

    Examples:
        >>> get_date_range(7)
        ('2025-01-03', '2025-01-10')
    """
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return from_date, to_date
