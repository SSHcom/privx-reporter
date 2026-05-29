"""Tests for timestamp parsing utilities."""

from datetime import UTC, datetime

import pytest

from lib._report.error import ValidationError
from lib.utils import date as timestamp_module

#### parse_iso_timestamp positive tests ####


@pytest.mark.unit
def test_parse_iso_timestamp_with_full_microseconds() -> None:
    """Test parse_iso_timestamp with full 6-digit microseconds."""
    timestamp_str = "2025-12-29T07:30:44.123456+00:00"

    result = timestamp_module.parse_iso_timestamp(timestamp_str)

    assert result == datetime(2025, 12, 29, 7, 30, 44, 123456, tzinfo=UTC)


@pytest.mark.unit
def test_parse_iso_timestamp_with_z_suffix() -> None:
    """Test parse_iso_timestamp with 'Z' suffix for UTC."""
    timestamp_str = "2025-12-29T07:30:44.123456Z"

    result = timestamp_module.parse_iso_timestamp(timestamp_str)

    assert result == datetime(2025, 12, 29, 7, 30, 44, 123456, tzinfo=UTC)


@pytest.mark.unit
def test_parse_iso_timestamp_without_microseconds() -> None:
    """Test parse_iso_timestamp without microseconds."""
    timestamp_str = "2025-12-29T07:30:44+00:00"

    result = timestamp_module.parse_iso_timestamp(timestamp_str)

    assert result == datetime(2025, 12, 29, 7, 30, 44, 0, tzinfo=UTC)


@pytest.mark.unit
def test_parse_iso_timestamp_without_microseconds_z_suffix() -> None:
    """Test parse_iso_timestamp without microseconds with 'Z' suffix."""
    timestamp_str = "2025-12-29T07:30:44Z"

    result = timestamp_module.parse_iso_timestamp(timestamp_str)

    assert result == datetime(2025, 12, 29, 7, 30, 44, 0, tzinfo=UTC)


@pytest.mark.unit
def test_parse_iso_timestamp_with_negative_timezone() -> None:
    """Test parse_iso_timestamp with negative timezone offset."""
    timestamp_str = "2025-12-29T07:30:44.123456-05:00"

    result = timestamp_module.parse_iso_timestamp(timestamp_str)

    # Verify the datetime is correct (timezone-aware)
    assert result.year == 2025
    assert result.month == 12
    assert result.day == 29
    assert result.hour == 7
    assert result.minute == 30
    assert result.second == 44
    assert result.microsecond == 123456
    assert result.tzinfo is not None


@pytest.mark.unit
def test_parse_iso_timestamp_with_positive_timezone() -> None:
    """Test parse_iso_timestamp with positive timezone offset."""
    timestamp_str = "2025-12-29T07:30:44.123456+05:30"

    result = timestamp_module.parse_iso_timestamp(timestamp_str)

    # Verify the datetime is correct (timezone-aware)
    assert result.year == 2025
    assert result.month == 12
    assert result.day == 29
    assert result.hour == 7
    assert result.minute == 30
    assert result.second == 44
    assert result.microsecond == 123456
    assert result.tzinfo is not None


#### parse_iso_timestamp negative tests ####


@pytest.mark.unit
def test_parse_iso_timestamp_invalid_format() -> None:
    """Test parse_iso_timestamp with invalid timestamp format."""
    timestamp_str = "not-a-timestamp"

    with pytest.raises(ValueError):
        timestamp_module.parse_iso_timestamp(timestamp_str)


@pytest.mark.unit
def test_parse_iso_timestamp_empty_string() -> None:
    """Test parse_iso_timestamp with empty string."""
    timestamp_str = ""

    with pytest.raises(ValueError):
        timestamp_module.parse_iso_timestamp(timestamp_str)


@pytest.mark.unit
def test_parse_iso_timestamp_invalid_date() -> None:
    """Test parse_iso_timestamp with invalid date (e.g., month 13)."""
    timestamp_str = "2025-13-29T07:30:44+00:00"

    with pytest.raises(ValueError):
        timestamp_module.parse_iso_timestamp(timestamp_str)


@pytest.mark.unit
def test_parse_iso_timestamp_invalid_time() -> None:
    """Test parse_iso_timestamp with invalid time (e.g., hour 25)."""
    timestamp_str = "2025-12-29T25:30:44+00:00"

    with pytest.raises(ValueError):
        timestamp_module.parse_iso_timestamp(timestamp_str)


@pytest.mark.unit
def test_parse_iso_timestamp_missing_timezone() -> None:
    """Test parse_iso_timestamp with missing timezone (returns naive datetime).

    Note: This returns a naive datetime (no timezone info), which may not be ideal
    but is the current behavior inherited from datetime.fromisoformat().
    """
    timestamp_str = "2025-12-29T07:30:44"

    result = timestamp_module.parse_iso_timestamp(timestamp_str)

    # Returns a naive datetime (tzinfo is None)
    assert result == datetime(2025, 12, 29, 7, 30, 44)
    assert result.tzinfo is None


#### validate_date tests ####


@pytest.mark.unit
def test_validate_date_with_yyyy_mm_dd_format() -> None:
    result = timestamp_module.validate_date("2026-01-15", "from_date")

    assert result == "2026-01-15T00:00:00.000000Z"


@pytest.mark.unit
def test_validate_date_with_end_of_day() -> None:
    result = timestamp_module.validate_date("2026-01-15", "to_date", end_of_day=True)

    assert result == "2026-01-15T23:59:59.999999Z"


@pytest.mark.unit
def test_validate_date_with_iso_format_passthrough() -> None:
    result = timestamp_module.validate_date("2026-01-15T12:30:00Z", "from_date")

    assert result == "2026-01-15T12:30:00Z"


@pytest.mark.unit
def test_validate_date_with_invalid_format_raises() -> None:
    with pytest.raises(ValidationError, match="Invalid from_date format"):
        timestamp_module.validate_date("not-a-date", "from_date")


#### format_iso_timestamp tests ####


@pytest.mark.unit
def test_format_iso_timestamp_with_utc() -> None:
    """Test format_iso_timestamp with UTC timezone."""
    dt = datetime(2025, 1, 9, 12, 0, 0, tzinfo=UTC)

    result = timestamp_module.format_iso_timestamp(dt)

    assert result == "2025-01-09T12:00:00Z"


@pytest.mark.unit
def test_format_iso_timestamp_with_microseconds() -> None:
    """Test format_iso_timestamp with microseconds."""
    dt = datetime(2025, 1, 9, 12, 0, 0, 123456, tzinfo=UTC)

    result = timestamp_module.format_iso_timestamp(dt)

    assert result == "2025-01-09T12:00:00.123456Z"


@pytest.mark.unit
def test_format_iso_timestamp_roundtrip() -> None:
    """Test that format_iso_timestamp and parse_iso_timestamp are inverse operations."""
    original_dt = datetime(2025, 1, 9, 12, 0, 0, 123456, tzinfo=UTC)

    formatted = timestamp_module.format_iso_timestamp(original_dt)
    parsed = timestamp_module.parse_iso_timestamp(formatted)

    assert parsed == original_dt
