"""Tests for role report helper functions."""

from unittest.mock import MagicMock, patch

import pytest

from reports.roles._shared.helpers import extract_role_restrictions, fetch_access_group_details


@pytest.mark.unit
@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (
            {
                "id": "role1",
                "name": "test-role",
                "context": {
                    "enabled": True,
                    "block_role": True,
                    "validity": ["MON", "TUE", "WED"],
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "timezone": "Europe/Helsinki",
                    "ip_masks": ["192.168.1.0/24", "10.0.0.0/8"],
                },
            },
            {
                "block_role": "True",
                "validity": "MON,TUE,WED",
                "start_time": "09:00",
                "end_time": "17:00",
                "timezone": "Europe/Helsinki",
                "ip_masks": "192.168.1.0/24,10.0.0.0/8",
            },
        ),
        (
            {"id": "role1", "name": "test-role"},
            {
                "block_role": "False",
                "validity": "",
                "start_time": "",
                "end_time": "",
                "timezone": "",
                "ip_masks": "",
            },
        ),
        (
            {
                "id": "role1",
                "name": "test-role",
                "context": {"enabled": True, "block_role": False, "timezone": "UTC"},
            },
            {
                "block_role": "False",
                "validity": "",
                "start_time": "",
                "end_time": "",
                "timezone": "UTC",
                "ip_masks": "",
            },
        ),
        (
            {
                "id": "role1",
                "name": "test-role",
                "context": {"enabled": True, "validity": [], "ip_masks": []},
            },
            {
                "block_role": "False",
                "validity": "",
                "start_time": "",
                "end_time": "",
                "timezone": "",
                "ip_masks": "",
            },
        ),
    ],
)
def test_extract_role_restrictions(role: dict, expected: dict[str, str]) -> None:
    assert extract_role_restrictions(role) == expected


@pytest.mark.unit
def test_fetch_access_group_details_empty_id() -> None:
    assert fetch_access_group_details(MagicMock(), "") == {
        "access_group_name": "",
        "access_group_comment": "",
        "access_group_default": False,
    }


@pytest.mark.unit
@patch("reports.roles._shared.helpers.get_access_group_by_id")
def test_fetch_access_group_details_found(mock_get_access_group_by_id: MagicMock) -> None:
    mock_get_access_group_by_id.return_value = {
        "name": "Production",
        "comment": "Main group",
        "default": True,
    }

    result = fetch_access_group_details(MagicMock(), "ag-1")

    assert result == {
        "access_group_name": "Production",
        "access_group_comment": "Main group",
        "access_group_default": True,
    }


@pytest.mark.unit
@patch("reports.roles._shared.helpers.get_access_group_by_id")
def test_fetch_access_group_details_not_found(mock_get_access_group_by_id: MagicMock) -> None:
    mock_get_access_group_by_id.return_value = None

    result = fetch_access_group_details(MagicMock(), "ag-missing")

    assert result == {
        "access_group_name": "",
        "access_group_comment": "",
        "access_group_default": False,
    }
