"""Tests for string utility functions."""

import pytest

from lib.utils.string import sanitize_string, to_ui_message


@pytest.mark.unit
def test_sanitize_string_basic() -> None:
    """Test that sanitize_string converts spaces and underscores to hyphens and lowercases the result."""
    assert sanitize_string("Hello World") == "hello-world"
    assert sanitize_string("test_string") == "test-string"


@pytest.mark.unit
def test_sanitize_string_lowercase() -> None:
    """Test that sanitize_string converts all characters to lowercase regardless of input case."""
    assert sanitize_string("UPPERCASE") == "uppercase"
    assert sanitize_string("MiXeD cAsE") == "mixed-case"


@pytest.mark.unit
def test_sanitize_string_special_characters() -> None:
    """Test that sanitize_string replaces special characters (like @, parentheses) with hyphens."""
    assert sanitize_string("test@example.com") == "test-example-com"
    assert sanitize_string("file(name)") == "file-name"


@pytest.mark.unit
def test_sanitize_string_multiple_hyphens() -> None:
    """Test that sanitize_string collapses multiple consecutive hyphens (or spaces) into a single hyphen."""
    assert sanitize_string("test---string") == "test-string"
    assert sanitize_string("test   string") == "test-string"


@pytest.mark.unit
def test_sanitize_string_leading_trailing_hyphens() -> None:
    """Test that sanitize_string removes leading and trailing hyphens from the result."""
    assert sanitize_string("-test-") == "test"
    assert sanitize_string("---test---") == "test"


@pytest.mark.unit
def test_sanitize_string_empty() -> None:
    """Test that sanitize_string returns an empty string when given an empty string input."""
    assert sanitize_string("") == ""


@pytest.mark.unit
def test_sanitize_string_only_special_chars() -> None:
    """Test that sanitize_string returns empty string when input has only special chars."""
    assert sanitize_string("!!!") == ""
    assert sanitize_string("---") == ""


@pytest.mark.unit
def test_to_ui_message_replaces_cli_option() -> None:
    assert to_ui_message("Use --host-address to filter") == 'Use "host address" to filter'


@pytest.mark.unit
def test_to_ui_message_handles_none() -> None:
    assert to_ui_message(None) is None


@pytest.mark.unit
def test_to_ui_message_preserves_non_option_text() -> None:
    assert to_ui_message("Regular message") == "Regular message"
