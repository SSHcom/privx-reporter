"""Tests for list validation utilities."""

import pytest

from lib.utils.dict import validate_dict_contains


@pytest.mark.unit
def test_validate_dict_contains_valid() -> None:
    """Test validation with valid data containing all required fields."""
    data = {
        "user_id": "user1",
        "role_name": "admin",
        "target_hosts": "host1.example.com",
        "target_accounts": "root",
    }
    required = ["user_id", "role_name", "target_hosts", "target_accounts"]

    validate_dict_contains(data, required)


@pytest.mark.unit
def test_validate_dict_contains_missing_fields() -> None:
    """Test validation raises error for missing fields."""
    data = {
        "user_id": "user1",
        "role_name": "admin",
    }
    required = ["user_id", "role_name", "target_hosts", "target_accounts"]

    with pytest.raises(
        ValueError, match="Data dictionary is missing required fields: \\['target_hosts', 'target_accounts'\\]"
    ):
        validate_dict_contains(data, required)


@pytest.mark.unit
def test_validate_dict_contains_partial_missing() -> None:
    """Test validation raises error when only some fields are missing."""
    data = {
        "user_id": "user1",
        "target_hosts": "host1.example.com",
    }
    required = ["user_id", "role_name", "target_hosts", "target_accounts"]

    with pytest.raises(
        ValueError, match="Data dictionary is missing required fields: \\['role_name', 'target_accounts'\\]"
    ):
        validate_dict_contains(data, required)
