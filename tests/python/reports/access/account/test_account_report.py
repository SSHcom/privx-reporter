"""Tests for host account access report functions."""

from unittest.mock import MagicMock, patch

import pytest

from lib.utils.config.report_ids import ReportIds
from reports.access._shared.models import AccountReportInputs
from reports.access.account import report as account_access_module


@pytest.mark.unit
def test_report_account_access_success(
    mock_report_api_host_account: MagicMock,
    mock_env_config_host_account: MagicMock,  # noqa
    mock_csv_writer_host_account: MagicMock,  # noqa
    mock_output_config_host_account: dict,
    standard_csv_dir: str,
    standard_batch_size: int,  # noqa
) -> None:
    """Test that report_account_access finds matching hosts/accounts and writes CSV."""
    mock_api = MagicMock()

    mock_report_api_host_account.hosts.search_hosts.return_value = {
        "count": 1,
        "items": [
            {
                "id": "host-123",
                "addresses": ["server1.example.com", "192.168.1.10"],
                "principals": [
                    {
                        "principal": "root",
                        "roles": [{"id": "role1", "name": "admin-role"}, {"id": "role2", "name": "user-role"}],
                    },
                    {"principal": "admin", "roles": []},
                ],
            }
        ],
    }

    mock_report_api_host_account.get_role_members.side_effect = [
        {
            "count": 2,
            "items": [
                {"id": "user1", "full_name": "User One"},
                {"id": "user2", "full_name": "User Two"},
            ],
        },
        {
            "count": 0,
            "items": [],
        },
    ]

    mock_report_api_host_account.get_report_out_dir.return_value = standard_csv_dir

    inputs = AccountReportInputs(target_address="server1.example.com", target_account="root")
    report_ids = ReportIds(
        command="access",
        sub_command="account",
        report_prefix="access-account",
        config_key="access.subcommands.account",
    )
    result = account_access_module.report_account_access(
        mock_api,
        inputs,
        mock_output_config_host_account,
        report_ids,
        None,
    )

    assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}


@pytest.mark.unit
def test_report_account_access_no_matches(
    mock_report_api_host_account: MagicMock,
    mock_env_config_host_account: MagicMock,  # noqa
    mock_csv_writer_host_account: MagicMock,  # noqa
    mock_output_config_host_account: dict,
) -> None:
    """Test that report_account_access returns info message when no match."""
    mock_api = MagicMock()

    mock_report_api_host_account.hosts.search_hosts.return_value = {
        "count": 1,
        "items": [
            {
                "id": "host-123",
                "addresses": ["different-host.example.com"],
                "principals": [{"principal": "root", "roles": []}],
            }
        ],
    }

    inputs = AccountReportInputs(target_address="server1.example.com", target_account="admin")
    report_ids = ReportIds(
        command="access",
        sub_command="account",
        report_prefix="access-account",
        config_key="access.subcommands.account",
    )
    result = account_access_module.report_account_access(
        mock_api,
        inputs,
        mock_output_config_host_account,
        report_ids,
        None,
    )

    assert result == {
        "report_path": None,
        "error_message": None,
        "info_message": "No users found who can access host 'server1.example.com' as account 'admin'",
    }


@pytest.mark.unit
def test_report_account_access_filters_hosts_by_user_group(
    mock_report_api_host_account: MagicMock,
    mock_output_config_host_account: dict,
) -> None:
    mock_api = MagicMock()

    mock_report_api_host_account.hosts.search_hosts.return_value = {
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
                "addresses": ["server1.example.com"],
                "principals": [{"principal": "root", "roles": [{"id": "role-2", "name": "role-2"}]}],
            },
        ],
    }
    mock_report_api_host_account.get_role_members.return_value = {
        "count": 1,
        "items": [{"id": "user1", "full_name": "User One"}],
    }

    with (
        patch.object(account_access_module, "resolve_allowed_access_group_ids", return_value=({"ag-1"}, None)),
        patch.object(account_access_module, "write_report_output") as mock_write,
    ):
        mock_write.return_value = {"report_path": "/tmp/report.csv", "error_message": None, "info_message": None}
        report_ids = ReportIds(
            command="access",
            sub_command="account",
            report_prefix="access-account",
            config_key="access.subcommands.account",
        )
        result = account_access_module.report_account_access(
            mock_api,
            AccountReportInputs(target_address="server1.example.com", target_account="root"),
            mock_output_config_host_account,
            report_ids,
            None,
            user_group_id="10",
        )

    assert result["error_message"] is None
    mock_report_api_host_account.get_role_members.assert_called_once_with(
        mock_api,
        role_id="role-1",
        offset=0,
        limit=100,
    )
