"""Tests for user role access map report functions."""

from unittest.mock import MagicMock, patch

import pytest

from lib.utils.config.report_ids import ReportIds
from reports.access._shared.models import RoleMapReportInputs
from reports.access.role_map import report as host_map_module


@pytest.mark.unit
def test_report_user_role_access_map_success(
    mock_report_api_user_access: MagicMock,
    mock_env_config_user_access: MagicMock,  # noqa
    mock_csv_writer_user_access: MagicMock,  # noqa
    mock_output_config_user_access: dict,
    standard_csv_dir: str,
) -> None:
    """Test that report_user_role_access_map retrieves hosts/members and writes CSV."""

    mock_api = MagicMock()

    mock_report_api_user_access.hosts.search_hosts.return_value = {
        "count": 1,
        "items": [
            {
                "id": "host-123",
                "addresses": ["host1.example.com", "host2.example.com"],
                "principals": [
                    {
                        "principal": "root",
                        "roles": [{"id": "role1", "name": "admin-role"}],
                    },
                    {
                        "principal": "admin",
                        "roles": [{"id": "role1", "name": "admin-role"}],
                    },
                ],
            }
        ],
    }

    mock_report_api_user_access.get_role_members.return_value = {
        "count": 2,
        "items": [
            {"id": "user1", "full_name": "User One"},
            {"id": "user2", "full_name": "User Two"},
        ],
    }

    mock_report_api_user_access.get_report_out_dir.return_value = standard_csv_dir

    inputs = RoleMapReportInputs(target_address="server1.example.com")
    report_ids = ReportIds(
        command="access",
        sub_command="role-map",
        report_prefix="access-role-map",
        config_key="access.subcommands.role-map",
    )
    result = host_map_module.report_user_role_access_map(
        mock_api,
        inputs,
        mock_output_config_user_access,
        report_ids,
        None,
    )

    assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}
    mock_report_api_user_access.hosts.search_hosts.assert_called_once_with(
        mock_api, search_payload={"keywords": "server1.example.com"}
    )


@pytest.mark.unit
def test_report_user_role_access_map_no_hosts_found(
    mock_report_api_user_access: MagicMock,
    mock_env_config_user_access: MagicMock,  # noqa
    mock_csv_writer_user_access: MagicMock,  # noqa
    mock_output_config_user_access: dict,
) -> None:
    """Test that report_user_role_access_map returns info message when no hosts found."""
    mock_api = MagicMock()

    mock_report_api_user_access.hosts.search_hosts.return_value = {
        "count": 0,
        "items": [],
    }

    inputs = RoleMapReportInputs(target_address="nonexistent.example.com")
    report_ids = ReportIds(
        command="access",
        sub_command="role-map",
        report_prefix="access-role-map",
        config_key="access.subcommands.role-map",
    )
    result = host_map_module.report_user_role_access_map(
        mock_api,
        inputs,
        mock_output_config_user_access,
        report_ids,
        None,
    )

    assert result == {
        "report_path": None,
        "error_message": None,
        "info_message": "No hosts found matching address 'nonexistent.example.com'",
    }
    mock_report_api_user_access.hosts.search_hosts.assert_called_once()
    mock_report_api_user_access.get_role_members.assert_not_called()


@pytest.mark.unit
def test_report_user_role_access_map_no_users_found(
    mock_report_api_user_access: MagicMock,
    mock_env_config_user_access: MagicMock,  # noqa
    mock_csv_writer_user_access: MagicMock,  # noqa
    mock_output_config_user_access: dict,
) -> None:
    """Test that report_user_role_access_map returns info message when no users found."""
    mock_api = MagicMock()

    mock_report_api_user_access.hosts.search_hosts.return_value = {
        "count": 1,
        "items": [
            {
                "id": "host-123",
                "addresses": ["server1.example.com"],
                "principals": [
                    {
                        "principal": "root",
                        "roles": [{"id": "role1", "name": "admin-role"}],
                    }
                ],
            }
        ],
    }

    mock_report_api_user_access.get_role_members.return_value = {
        "count": 0,
        "items": [],
    }

    inputs = RoleMapReportInputs(target_address="server1.example.com")
    report_ids = ReportIds(
        command="access",
        sub_command="role-map",
        report_prefix="access-role-map",
        config_key="access.subcommands.role-map",
    )
    result = host_map_module.report_user_role_access_map(
        mock_api,
        inputs,
        mock_output_config_user_access,
        report_ids,
        None,
    )

    assert result == {
        "report_path": None,
        "error_message": None,
        "info_message": "No users found who can access host 'server1.example.com'",
    }


@pytest.mark.unit
def test_report_user_role_access_map_with_pagination(
    mock_report_api_user_access: MagicMock,
    mock_env_config_user_access: MagicMock,  # noqa
    mock_csv_writer_user_access: MagicMock,  # noqa
    mock_output_config_user_access: dict,
    standard_csv_dir: str,
) -> None:
    """Test that report_user_role_access_map correctly handles paginated member retrieval."""
    mock_api = MagicMock()

    mock_report_api_user_access.hosts.search_hosts.return_value = {
        "count": 1,
        "items": [
            {
                "id": "host-123",
                "addresses": ["server1.example.com"],
                "principals": [
                    {
                        "principal": "root",
                        "roles": [{"id": "role1", "name": "admin-role"}],
                    }
                ],
            }
        ],
    }

    mock_report_api_user_access.get_role_members.side_effect = [
        {
            "count": 3,
            "items": [
                {"id": "user1", "full_name": "User One"},
                {"id": "user2", "full_name": "User Two"},
            ],
        },
        {
            "count": 3,
            "items": [
                {"id": "user3", "full_name": "User Three"},
            ],
        },
    ]

    mock_report_api_user_access.get_report_out_dir.return_value = standard_csv_dir

    inputs = RoleMapReportInputs(target_address="server1.example.com")
    report_ids = ReportIds(
        command="access",
        sub_command="role-map",
        report_prefix="access-role-map",
        config_key="access.subcommands.role-map",
    )
    result = host_map_module.report_user_role_access_map(
        mock_api,
        inputs,
        mock_output_config_user_access,
        report_ids,
        None,
    )

    assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}
    assert mock_report_api_user_access.get_role_members.call_count == 2


@pytest.mark.unit
def test_report_user_role_access_map_filters_hosts_by_user_group(
    mock_report_api_user_access: MagicMock,
    mock_output_config_user_access: dict,
) -> None:
    mock_api = MagicMock()
    mock_report_api_user_access.hosts.search_hosts.return_value = {
        "count": 2,
        "items": [
            {
                "id": "host-allowed",
                "access_group_id": "ag-1",
                "addresses": ["server1.example.com"],
                "principals": [{"principal": "root", "roles": [{"id": "role-1", "name": "role-1"}]}],
            },
            {
                "id": "host-blocked",
                "access_group_id": "ag-2",
                "addresses": ["server2.example.com"],
                "principals": [{"principal": "root", "roles": [{"id": "role-2", "name": "role-2"}]}],
            },
        ],
    }
    mock_report_api_user_access.get_role_members.return_value = {
        "count": 1,
        "items": [{"id": "user1", "full_name": "User One"}],
    }

    with (
        patch.object(host_map_module, "resolve_allowed_access_group_ids", return_value=({"ag-1"}, None)),
        patch.object(host_map_module, "write_report_output") as mock_write,
    ):
        mock_write.return_value = {"report_path": "/tmp/report.csv", "error_message": None, "info_message": None}
        result = host_map_module.report_user_role_access_map(
            mock_api,
            RoleMapReportInputs(target_address="server"),
            mock_output_config_user_access,
            ReportIds(
                command="access",
                sub_command="role-map",
                report_prefix="access-role-map",
                config_key="access.subcommands.role-map",
            ),
            None,
            user_group_id="10",
        )

    assert result["error_message"] is None
    output_rows = mock_write.call_args[0][4]
    assert len(output_rows) == 1
    assert output_rows[0]["target_host"] == "server1.example.com"
