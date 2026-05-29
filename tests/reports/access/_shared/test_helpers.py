"""Tests for shared helper functions in access reports."""

from unittest.mock import MagicMock, patch

import pytest

from reports.access._shared import helpers


@pytest.mark.unit
def test_fetch_all_role_members_paginates_until_total_count() -> None:
    """Fetch all role members across multiple pages."""
    mock_api = MagicMock()

    with (
        patch.object(helpers.EnvConfig, "get_api_batchsize", return_value=2),
        patch.object(helpers, "report_api") as mock_report_api,
    ):
        mock_report_api.get_role_members.side_effect = [
            {
                "count": 3,
                "items": [
                    {"id": "u1", "full_name": "User One"},
                    {"id": "u2", "full_name": "User Two"},
                ],
            },
            {
                "count": 3,
                "items": [
                    {"id": "u3", "full_name": "User Three"},
                ],
            },
        ]

        members = helpers.fetch_all_role_members(mock_api, "role-1")

    assert members == [
        {"id": "u1", "full_name": "User One"},
        {"id": "u2", "full_name": "User Two"},
        {"id": "u3", "full_name": "User Three"},
    ]
    assert mock_report_api.get_role_members.call_count == 2
    mock_report_api.get_role_members.assert_any_call(mock_api, role_id="role-1", offset=0, limit=2)
    mock_report_api.get_role_members.assert_any_call(mock_api, role_id="role-1", offset=2, limit=2)


@pytest.mark.unit
def test_fetch_all_role_members_stops_when_page_is_empty() -> None:
    """Stop pagination when API returns empty items."""
    mock_api = MagicMock()

    with (
        patch.object(helpers.EnvConfig, "get_api_batchsize", return_value=2),
        patch.object(helpers, "report_api") as mock_report_api,
    ):
        mock_report_api.get_role_members.side_effect = [
            {
                "count": 10,
                "items": [
                    {"id": "u1", "full_name": "User One"},
                ],
            },
            {"count": 10, "items": []},
        ]

        members = helpers.fetch_all_role_members(mock_api, "role-1")

    assert members == [{"id": "u1", "full_name": "User One"}]
    assert mock_report_api.get_role_members.call_count == 2


@pytest.mark.unit
def test_group_hosts_by_account_groups_addresses_and_ids() -> None:
    """Group hosts by joined account names."""
    hosts_data = [
        {
            "id": "host-2",
            "addresses": ["b.example.com"],
            "principals": [{"principal": "admin"}],
        },
        {
            "id": "host-1",
            "addresses": ["a.example.com"],
            "principals": [{"principal": "root"}, {"principal": "admin"}],
        },
        {
            "id": "host-3",
            "addresses": ["c.example.com"],
            "principals": [{"principal": ""}],
        },
        {
            "id": "host-no-address",
            "addresses": [],
            "principals": [{"principal": "skip-me"}],
        },
    ]

    grouped = helpers.group_hosts_by_account(hosts_data)

    assert grouped["admin"] == {"addresses": ["b.example.com"], "ids": ["host-2"]}
    assert grouped["root,admin"] == {"addresses": ["a.example.com"], "ids": ["host-1"]}
    assert grouped[""] == {"addresses": ["c.example.com"], "ids": ["host-3"]}
    assert "host-no-address" not in str(grouped)
