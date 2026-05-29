"""Tests for host user restrict report functions."""

from unittest.mock import MagicMock, patch

import pytest

from lib.utils.config.report_ids import ReportIds
from reports.access._shared.models import AccountRestrictionsReportInputs
from reports.access.account_restrictions import report as account_restrictions_module


@pytest.mark.unit
def test_report_account_restrictions_success(
    mock_api: MagicMock,
    mock_report_api_hosts: MagicMock,
    mock_env_config_hosts: MagicMock,  # noqa
    mock_csv_writer_hosts: MagicMock,  # noqa
    mock_output_config_host_user_restrict: dict,
    standard_csv_dir: str,
) -> None:
    """Test host command restrictions are correctly retrieved and written to CSV."""

    mock_report_api_hosts.hosts.search_hosts.return_value = {
        "count": 1,
        "items": [
            {
                "id": "host-123",
                "common_name": "server1",
                "addresses": ["server1.example.com", "192.168.1.10"],
            }
        ],
    }

    mock_report_api_hosts.hosts.get_host.return_value = {
        "id": "host-123",
        "addresses": ["server1.example.com", "192.168.1.10"],
        "principals": [
            {
                "principal": "root",
                "command_restrictions": {
                    "enabled": True,
                    "default_whitelist": {"id": "wl-1", "name": "DefaultWL"},
                    "whitelists": [
                        {"whitelist": {"id": "wl-2", "name": "CustomWL1"}},
                        {"whitelist": {"id": "wl-3", "name": "CustomWL2"}},
                    ],
                    "allow_no_match": True,
                    "audit_match": False,
                    "audit_no_match": True,
                },
            },
            {
                "principal": "admin",
                "command_restrictions": {"enabled": False},
            },
        ],
    }

    mock_report_api_hosts.get_report_out_dir.return_value = standard_csv_dir

    inputs = AccountRestrictionsReportInputs(target_address="server1.example.com")
    report_ids = ReportIds(
        command="access",
        sub_command="account-restrictions",
        report_prefix="access-account-restrictions",
        config_key="access.subcommands.account-restrictions",
    )
    result = account_restrictions_module.report_account_restrictions(
        mock_api,
        inputs,
        mock_output_config_host_user_restrict,
        report_ids,
        None,
    )

    assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}
    mock_report_api_hosts.hosts.search_hosts.assert_called_once_with(
        mock_api, search_payload={"keywords": "server1.example.com"}, offset=0, limit=100
    )
    mock_report_api_hosts.hosts.get_host.assert_called_once_with(mock_api, "host-123")


@pytest.mark.unit
def test_report_account_restrictions_no_hosts_found(
    mock_api: MagicMock,
    mock_report_api_hosts: MagicMock,
    mock_env_config_hosts: MagicMock,  # noqa
    mock_csv_writer_hosts: MagicMock,  # noqa
    mock_output_config_host_user_restrict: dict,
) -> None:
    """Test that report_account_restrictions skips CSV when no hosts match search criteria."""

    mock_report_api_hosts.hosts.search_hosts.return_value = {"count": 0, "items": []}

    inputs = AccountRestrictionsReportInputs(target_address="nonexistent.example.com")
    report_ids = ReportIds(
        command="access",
        sub_command="account-restrictions",
        report_prefix="access-account-restrictions",
        config_key="access.subcommands.account-restrictions",
    )
    result = account_restrictions_module.report_account_restrictions(
        mock_api,
        inputs,
        mock_output_config_host_user_restrict,
        report_ids,
        None,
    )

    assert result == {
        "report_path": None,
        "error_message": None,
        "info_message": "No users with command restrictions found on host 'nonexistent.example.com'",
    }
    mock_report_api_hosts.hosts.search_hosts.assert_called_once()
    mock_report_api_hosts.hosts.get_host.assert_not_called()


@pytest.mark.unit
def test_report_account_restrictions_no_restrictions_enabled(
    mock_api: MagicMock,
    mock_report_api_hosts: MagicMock,
    mock_env_config_hosts: MagicMock,  # noqa
    mock_csv_writer_hosts: MagicMock,  # noqa
    mock_output_config_host_user_restrict: dict,
) -> None:
    """Test that report_account_restrictions skips CSV when host has no enabled restrictions."""

    mock_report_api_hosts.hosts.search_hosts.return_value = {
        "count": 1,
        "items": [{"id": "host-123", "addresses": ["server1.example.com"]}],
    }

    mock_report_api_hosts.hosts.get_host.return_value = {
        "id": "host-123",
        "addresses": ["server1.example.com"],
        "principals": [
            {"principal": "root", "command_restrictions": {"enabled": False}},
            {"principal": "admin"},
        ],
    }

    inputs = AccountRestrictionsReportInputs(target_address="server1.example.com")
    report_ids = ReportIds(
        command="access",
        sub_command="account-restrictions",
        report_prefix="access-account-restrictions",
        config_key="access.subcommands.account-restrictions",
    )
    result = account_restrictions_module.report_account_restrictions(
        mock_api,
        inputs,
        mock_output_config_host_user_restrict,
        report_ids,
        None,
    )

    assert result == {
        "report_path": None,
        "error_message": None,
        "info_message": "No users with command restrictions found on host 'server1.example.com'",
    }
    mock_report_api_hosts.hosts.get_host.assert_called_once()


@pytest.mark.unit
def test_report_account_restrictions_get_host_fails(
    mock_api: MagicMock,
    mock_report_api_hosts: MagicMock,
    mock_env_config_hosts: MagicMock,  # noqa
    mock_csv_writer_hosts: MagicMock,  # noqa
    mock_output_config_host_user_restrict: dict,
) -> None:
    """Test that report_account_restrictions logs error and does not write CSV when get_host raises an exception."""

    mock_report_api_hosts.hosts.search_hosts.return_value = {
        "count": 1,
        "items": [{"id": "host-123", "addresses": ["server1.example.com"]}],
    }

    mock_report_api_hosts.hosts.get_host.side_effect = Exception("API error")

    with patch.object(account_restrictions_module, "logger") as mock_logger:
        inputs = AccountRestrictionsReportInputs(target_address="server1.example.com")
        report_ids = ReportIds(
            command="access",
            sub_command="account-restrictions",
            report_prefix="access-account-restrictions",
            config_key="access.subcommands.account-restrictions",
        )
        result = account_restrictions_module.report_account_restrictions(
            mock_api,
            inputs,
            mock_output_config_host_user_restrict,
            report_ids,
            None,
        )

    assert result == {
        "report_path": None,
        "error_message": None,
        "info_message": "No users with command restrictions found on host 'server1.example.com'",
    }
    mock_report_api_hosts.hosts.get_host.assert_called_once()
    mock_logger.error.assert_called_once()


@pytest.mark.unit
def test_report_account_restrictions_no_target_address(
    mock_api: MagicMock,
    mock_report_api_hosts: MagicMock,
    mock_env_config_hosts: MagicMock,  # noqa
    mock_csv_writer_hosts: MagicMock,  # noqa
    mock_output_config_host_user_restrict: dict,
    standard_csv_dir: str,
) -> None:
    """Test report_account_restrictions when target_address is not provided (searches all hosts)."""

    mock_report_api_hosts.hosts.search_hosts.return_value = {
        "count": 2,
        "items": [
            {
                "id": "host-123",
                "common_name": "server1",
                "addresses": ["server1.example.com", "192.168.1.10"],
            },
            {
                "id": "host-456",
                "common_name": "server2",
                "addresses": ["server2.example.com"],
            },
        ],
    }

    def get_host_side_effect(api: MagicMock, host_id: str) -> dict:
        if host_id == "host-123":
            return {
                "id": "host-123",
                "addresses": ["server1.example.com", "192.168.1.10"],
                "principals": [
                    {
                        "principal": "root",
                        "command_restrictions": {
                            "enabled": True,
                            "default_whitelist": {"id": "wl-1", "name": "DefaultWL"},
                            "whitelists": [],
                            "allow_no_match": True,
                            "audit_match": False,
                            "audit_no_match": True,
                        },
                    },
                ],
            }
        else:
            return {
                "id": "host-456",
                "addresses": ["server2.example.com"],
                "principals": [
                    {"principal": "admin", "command_restrictions": {"enabled": False}},
                ],
            }

    mock_report_api_hosts.hosts.get_host.side_effect = get_host_side_effect
    mock_report_api_hosts.get_report_out_dir.return_value = standard_csv_dir

    inputs = AccountRestrictionsReportInputs(target_address="")
    report_ids = ReportIds(
        command="access",
        sub_command="account-restrictions",
        report_prefix="access-account-restrictions",
        config_key="access.subcommands.account-restrictions",
    )
    result = account_restrictions_module.report_account_restrictions(
        mock_api,
        inputs,
        mock_output_config_host_user_restrict,
        report_ids,
        None,
    )

    assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}
    mock_report_api_hosts.hosts.search_hosts.assert_called_once_with(mock_api, search_payload={}, offset=0, limit=100)


@pytest.mark.unit
def test_report_account_restrictions_no_target_address_no_restrictions(
    mock_api: MagicMock,
    mock_report_api_hosts: MagicMock,
    mock_env_config_hosts: MagicMock,  # noqa
    mock_csv_writer_hosts: MagicMock,  # noqa
    mock_output_config_host_user_restrict: dict,
) -> None:
    """Test report_account_restrictions with no target_address and no restrictions found."""

    mock_report_api_hosts.hosts.search_hosts.return_value = {
        "count": 1,
        "items": [
            {
                "id": "host-123",
                "addresses": ["server1.example.com"],
            },
        ],
    }

    mock_report_api_hosts.hosts.get_host.return_value = {
        "id": "host-123",
        "addresses": ["server1.example.com"],
        "principals": [
            {"principal": "root", "command_restrictions": {"enabled": False}},
        ],
    }

    inputs = AccountRestrictionsReportInputs(target_address="")
    report_ids = ReportIds(
        command="access",
        sub_command="account-restrictions",
        report_prefix="access-account-restrictions",
        config_key="access.subcommands.account-restrictions",
    )
    result = account_restrictions_module.report_account_restrictions(
        mock_api,
        inputs,
        mock_output_config_host_user_restrict,
        report_ids,
        None,
    )

    assert result == {
        "report_path": None,
        "error_message": None,
        "info_message": "No users with command restrictions found",
    }
    mock_report_api_hosts.hosts.search_hosts.assert_called_once_with(mock_api, search_payload={}, offset=0, limit=100)


@pytest.mark.unit
def test_report_account_restrictions_filters_hosts_by_user_group(
    mock_api: MagicMock,
    mock_report_api_hosts: MagicMock,
    mock_output_config_host_user_restrict: dict,
    standard_csv_dir: str,
) -> None:
    mock_report_api_hosts.hosts.search_hosts.side_effect = [
        {
            "count": 2,
            "items": [
                {"id": "host-allowed", "access_group_id": "ag-1", "addresses": ["server1.example.com"]},
                {"id": "host-blocked", "access_group_id": "ag-2", "addresses": ["server2.example.com"]},
            ],
        },
        {"count": 2, "items": []},
    ]
    mock_report_api_hosts.hosts.get_host.return_value = {
        "id": "host-allowed",
        "addresses": ["server1.example.com"],
        "principals": [
            {
                "principal": "root",
                "command_restrictions": {
                    "enabled": True,
                    "default_whitelist": {"id": "wl-1", "name": "DefaultWL"},
                    "whitelists": [],
                    "allow_no_match": False,
                    "audit_match": False,
                    "audit_no_match": False,
                },
            }
        ],
    }
    mock_report_api_hosts.get_report_out_dir.return_value = standard_csv_dir

    with patch.object(
        account_restrictions_module,
        "resolve_allowed_access_group_ids",
        return_value=({"ag-1"}, None),
    ):
        result = account_restrictions_module.report_account_restrictions(
            mock_api,
            AccountRestrictionsReportInputs(target_address=""),
            mock_output_config_host_user_restrict,
            ReportIds(
                command="access",
                sub_command="account-restrictions",
                report_prefix="access-account-restrictions",
                config_key="access.subcommands.account-restrictions",
            ),
            None,
            user_group_id="10",
        )

    assert result["error_message"] is None
    mock_report_api_hosts.hosts.get_host.assert_called_once_with(mock_api, "host-allowed")
