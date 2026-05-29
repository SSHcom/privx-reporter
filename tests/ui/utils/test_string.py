"""Tests for UI string helpers."""

import pytest

from ui.utils.string import normalize_name


@pytest.mark.unit
def test_normalize_name_replaces_underscores() -> None:
    assert normalize_name("user_hosts") == "User hosts"


@pytest.mark.unit
def test_normalize_name_replaces_dashes() -> None:
    assert normalize_name("access-control") == "Access control"


@pytest.mark.unit
def test_normalize_name_empty_string_returns_empty() -> None:
    assert normalize_name("") == ""


@pytest.mark.unit
def test_normalize_name_whitespace_only_returns_empty() -> None:
    assert normalize_name("   ") == ""


@pytest.mark.unit
def test_normalize_name_collapses_multiple_separators() -> None:
    assert normalize_name("foo__bar") == "Foo bar"
