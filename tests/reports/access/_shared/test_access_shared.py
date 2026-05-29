"""Tests for shared access report utility functions."""

import pytest

from reports.access._shared.helpers import get_username_info


@pytest.mark.unit
def test_get_username_info_fallback_chain() -> None:
    """
    Test get_username_info fallback chain:
    principal -> samaccountname -> distinguished_name -> 'UserID not found'.
    """
    members_data = {
        "items": [
            {"principal": "user1", "samaccountname": "user1_sam"},  # Uses principal
            {"samaccountname": "user2_sam", "distinguished_name": "CN=user2"},  # Uses samaccountname
            {"distinguished_name": "CN=user3,OU=Users"},  # Uses distinguished_name
            {"email": "user4@example.com"},  # No username attributes -> fallback
        ]
    }

    result = get_username_info(members_data)

    assert result == ["user1", "user2_sam", "CN=user3,OU=Users", "UserID not found"]


@pytest.mark.unit
def test_get_username_info_empty_principal_uses_fallback() -> None:
    """Test that get_username_info falls back to samaccountname or distinguished_name."""
    members_data = {
        "items": [
            {"principal": "", "samaccountname": "user1_sam"},
            {"principal": None, "distinguished_name": "CN=user2"},
        ]
    }

    result = get_username_info(members_data)

    assert result == ["user1_sam", "CN=user2"]


@pytest.mark.unit
def test_get_username_info_empty_or_missing_items() -> None:
    """Test that get_username_info returns empty list when items is empty or missing."""
    assert get_username_info({"items": []}) == []
    assert get_username_info({}) == []
