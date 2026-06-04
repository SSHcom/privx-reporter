"""Tests for user hosts access report functions."""

from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lib.utils.config.report_ids import ReportIds
from reports.access._shared.models import HostsReportInputs
from reports.access.hosts import report as hosts_access_module


@pytest.fixture
def mock_report_api_user_hosts() -> MagicMock:
    """Fixture for mocking report API in hosts_access module."""
    with patch.object(hosts_access_module, "report_api") as mock:
        yield mock


@pytest.fixture
def mock_write_report_output(standard_csv_dir: str) -> Iterator[MagicMock]:
    """Fixture for mocking write_report_output."""
    with patch.object(hosts_access_module, "write_report_output") as mock:
        mock.return_value = {"report_path": standard_csv_dir, "error_message": None, "info_message": None}
        yield mock


@pytest.fixture
def mock_output_config_user_hosts() -> dict:
    """Fixture for mock output configuration for user hosts access report."""
    return {
        "access": {
            "subcommands": {
                "hosts": {
                    "fields": {
                        "user_id": "true|User ID",
                        "user_name": "true|User Name",
                        "principal": "true|Principal",
                        "source_name": "true|Source",
                        "role_id": "true|Role ID",
                        "role_name": "true|Role Name",
                        "target_host": "true|Target Host",
                        "target_host_name": "true|Target Host Name",
                        "target_host_id": "true|Target Host ID",
                        "target_accounts": "true|Target Accounts",
                    }
                }
            }
        }
    }


@pytest.mark.unit
def test_report_hosts_access_success(
    mock_report_api_user_hosts: MagicMock,
    mock_write_report_output: MagicMock,
    mock_output_config_user_hosts: dict,
    standard_csv_dir: str,
) -> None:
    """Test that report_hosts_access retrieves users, roles, hosts and writes output."""
    mock_api = MagicMock()
    mock_api.get_sources.return_value = MagicMock(ok=True, data={"items": [{"id": "source-1", "name": "Local"}]})
    mock_report_api_user_hosts.users.search_users.return_value = {
        "count": 1,
        "items": [
            {"id": "user123", "full_name": "user123", "principal": "userone", "source": "source-1"},
        ],
    }
    mock_report_api_user_hosts.get_user_roles.return_value = [
        {"id": "role1", "name": "admin-role"},
    ]
    mock_report_api_user_hosts.hosts.search_hosts.return_value = {
        "count": 1,
        "items": [
            {
                "id": "host-1",
                "addresses": ["host1.example.com"],
                "common_name": "host1",
                "principals": [
                    {
                        "principal": "root",
                        "roles": [{"id": "role1", "name": "admin-role"}],
                    },
                ],
            },
        ],
    }
    inputs = HostsReportInputs(user_name="user123")
    report_ids = ReportIds(
        command="access",
        sub_command="hosts",
        report_prefix="access-hosts",
        config_key="access.subcommands.hosts",
    )
    result = hosts_access_module.report_hosts_access(
        mock_api,
        inputs,
        mock_output_config_user_hosts,
        report_ids,
        None,
    )
    assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}
    mock_report_api_user_hosts.users.search_users.assert_called_once_with(
        mock_api, search_payload={"keywords": "user123"}
    )
    mock_report_api_user_hosts.hosts.search_hosts.assert_called_once_with(
        mock_api, search_payload={}, offset=0, limit=100
    )


@pytest.mark.unit
def test_report_hosts_access_no_user_found(
    mock_report_api_user_hosts: MagicMock,
    mock_write_report_output: MagicMock,
    mock_output_config_user_hosts: dict,
) -> None:
    """Test that report_hosts_access returns info message when user is not found."""
    mock_api = MagicMock()
    mock_api.get_sources.return_value = MagicMock(ok=True, data={"items": []})
    mock_report_api_user_hosts.users.search_users.return_value = {"count": 0, "items": []}
    inputs = HostsReportInputs(user_name="nonexistent_user")
    report_ids = ReportIds(
        command="access",
        sub_command="hosts",
        report_prefix="access-hosts",
        config_key="access.subcommands.hosts",
    )
    result = hosts_access_module.report_hosts_access(
        mock_api,
        inputs,
        mock_output_config_user_hosts,
        report_ids,
        None,
    )
    assert result == {
        "report_path": None,
        "error_message": None,
        "info_message": (
            "No exact match found for user name 'nonexistent_user'. "
            "Please try with the complete username or use --principal instead."
        ),
    }
    mock_report_api_user_hosts.users.search_users.assert_called_once()
    mock_report_api_user_hosts.get_user_roles.assert_not_called()


@pytest.mark.unit
def test_report_hosts_access_no_roles(
    mock_report_api_user_hosts: MagicMock,
    mock_write_report_output: MagicMock,
    mock_output_config_user_hosts: dict,
) -> None:
    """Test that report_hosts_access returns info message when user has no roles."""
    mock_api = MagicMock()
    mock_api.get_sources.return_value = MagicMock(ok=True, data={"items": [{"id": "source-1", "name": "Local"}]})
    mock_report_api_user_hosts.users.search_users.return_value = {
        "count": 1,
        "items": [
            {"id": "user123", "full_name": "user123", "principal": "userone", "source": "source-1"},
        ],
    }
    mock_report_api_user_hosts.get_user_roles.return_value = []
    inputs = HostsReportInputs(user_name="user123")
    report_ids = ReportIds(
        command="access",
        sub_command="hosts",
        report_prefix="access_host",
        config_key="access.subcommands.hosts",
    )
    result = hosts_access_module.report_hosts_access(
        mock_api,
        inputs,
        mock_output_config_user_hosts,
        report_ids,
        None,
    )
    assert result == {
        "report_path": None,
        "error_message": None,
        "info_message": "No roles found for any of the matched users.",
    }


@pytest.mark.unit
def test_report_hosts_access_no_hosts_for_roles(
    mock_report_api_user_hosts: MagicMock,
    mock_write_report_output: MagicMock,
    mock_output_config_user_hosts: dict,
) -> None:
    """Test that report_hosts_access returns info message when roles have no hosts."""
    mock_api = MagicMock()
    mock_api.get_sources.return_value = MagicMock(ok=True, data={"items": [{"id": "source-1", "name": "Local"}]})
    mock_report_api_user_hosts.users.search_users.return_value = {
        "count": 1,
        "items": [
            {"id": "user123", "full_name": "user123", "principal": "userone", "source": "source-1"},
        ],
    }
    mock_report_api_user_hosts.get_user_roles.return_value = [
        {"id": "role1", "name": "admin-role"},
    ]
    mock_report_api_user_hosts.hosts.search_hosts.return_value = {"count": 0, "items": []}
    inputs = HostsReportInputs(user_name="user123")
    report_ids = ReportIds(
        command="access",
        sub_command="host",
        report_prefix="access-hosts",
        config_key="access.subcommands.hosts",
    )
    result = hosts_access_module.report_hosts_access(
        mock_api,
        inputs,
        mock_output_config_user_hosts,
        report_ids,
        None,
    )
    assert result == {
        "report_path": None,
        "error_message": None,
        "info_message": "No hosts found for any of the 1 matched user(s)",
    }


@pytest.mark.unit
def test_report_hosts_access_multiple_users(
    mock_report_api_user_hosts: MagicMock,
    mock_write_report_output: MagicMock,
    mock_output_config_user_hosts: dict,
    standard_csv_dir: str,
) -> None:
    """Test that report_hosts_access handles multiple matched users."""
    mock_api = MagicMock()
    mock_api.get_sources.return_value = MagicMock(ok=True, data={"items": [{"id": "source-1", "name": "Local"}]})
    mock_report_api_user_hosts.users.search_users.return_value = {
        "count": 2,
        "items": [
            {"id": "user1", "full_name": "user", "principal": "userone", "source": "source-1"},
            {"id": "user2", "full_name": "user", "principal": "usertwo", "source": "source-1"},
        ],
    }

    def get_user_roles_side_effect(api: object, user_id: str) -> list[dict[str, Any]]:
        if user_id == "user1":
            return [{"id": "role1", "name": "admin-role"}]
        elif user_id == "user2":
            return [{"id": "role2", "name": "user-role"}]
        return []

    mock_report_api_user_hosts.get_user_roles.side_effect = get_user_roles_side_effect
    mock_report_api_user_hosts.hosts.search_hosts.return_value = {
        "map": {"id": "source-1", "name": "Local"},
        "count": 2,
        "items": [
            {
                "id": "host-1",
                "addresses": ["host1.example.com"],
                "common_name": "host1",
                "principals": [
                    {"principal": "root", "roles": [{"id": "role1", "name": "admin-role"}]},
                ],
            },
            {
                "id": "host-2",
                "addresses": ["host2.example.com"],
                "common_name": "host2",
                "principals": [
                    {"principal": "user", "roles": [{"id": "role2", "name": "user-role"}]},
                ],
            },
        ],
    }
    inputs = HostsReportInputs(user_name="user")
    report_ids = ReportIds(
        command="access",
        sub_command="hosts",
        report_prefix="access-hosts",
        config_key="access.subcommands.hosts",
    )
    result = hosts_access_module.report_hosts_access(
        mock_api,
        inputs,
        mock_output_config_user_hosts,
        report_ids,
        None,
    )
    assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}
    assert mock_report_api_user_hosts.get_user_roles.call_count == 2


@pytest.mark.unit
@pytest.mark.parametrize(
    ("directory", "expected_role_calls", "expected_info"),
    [
        ("MICROSOFTGRAPH", 1, None),
        ("ldap", 1, None),
        ("LDAP-NO-MATCH", 0, "No users found with directory 'LDAP-NO-MATCH'"),
        ("", 2, None),
    ],
)
def test_report_hosts_access_directory_filter_variants(
    mock_report_api_user_hosts: MagicMock,
    mock_write_report_output: MagicMock,
    mock_output_config_user_hosts: dict,
    standard_csv_dir: str,
    directory: str,
    expected_role_calls: int,
    expected_info: str | None,
) -> None:
    """Directory filter should match, ignore case, reject no-match, or include all when omitted."""
    mock_api = MagicMock()
    users = [
        {
            "id": "user-local",
            "full_name": "ralph",
            "principal": "rwu",
            "source_type": "LOCAL",
            "source": "source-local",
        },
        {
            "id": "user-aad",
            "full_name": "ralph",
            "principal": "ralph.wu@sshdemo.net",
            "source_type": "MICROSOFTGRAPH",
            "source": "source-aad",
        },
    ]
    if directory == "ldap":
        users[1]["id"] = "user-ldap"
        users[1]["source_type"] = "LDAP"

    mock_api.get_sources.return_value = MagicMock(
        ok=True,
        data={"items": [{"id": "source-aad", "name": "AAD"}, {"id": "source-local", "name": "Local"}]},
    )
    mock_report_api_user_hosts.users.search_users.return_value = {
        "count": 2,
        "items": users,
    }
    mock_report_api_user_hosts.get_user_roles.return_value = [
        {"id": "role1", "name": "admin-role"},
    ]
    mock_report_api_user_hosts.hosts.search_hosts.return_value = {
        "count": 1,
        "items": [
            {
                "id": "host-1",
                "addresses": ["host1.example.com"],
                "common_name": "host1",
                "principals": [
                    {"principal": "root", "roles": [{"id": "role1", "name": "admin-role"}]},
                ],
            },
        ],
    }
    inputs = HostsReportInputs(user_name="ralph", directory=directory)
    report_ids = ReportIds(
        command="access",
        sub_command="hosts",
        report_prefix="access-hosts",
        config_key="access.subcommands.hosts",
    )
    result = hosts_access_module.report_hosts_access(
        mock_api,
        inputs,
        mock_output_config_user_hosts,
        report_ids,
        None,
    )
    if expected_info:
        assert result == {"report_path": None, "error_message": None, "info_message": expected_info}
        mock_report_api_user_hosts.hosts.search_hosts.assert_not_called()
    else:
        assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}
    assert mock_report_api_user_hosts.get_user_roles.call_count == expected_role_calls


@pytest.mark.unit
def test_host_has_role() -> None:
    """Test the _host_has_role helper function."""
    host = {
        "principals": [
            {"principal": "root", "roles": [{"id": "role1", "name": "admin"}]},
            {"principal": "user", "roles": [{"id": "role2", "name": "user"}]},
        ]
    }
    assert hosts_access_module._host_has_role(host, "role1") is True
    assert hosts_access_module._host_has_role(host, "role2") is True
    assert hosts_access_module._host_has_role(host, "role3") is False


@pytest.mark.unit
def test_host_has_role_no_principals() -> None:
    """Test _host_has_role with host that has no principals."""
    host = {}
    assert hosts_access_module._host_has_role(host, "role1") is False


@pytest.mark.unit
def test_build_access_entry() -> None:
    """Test the _build_access_entry helper function."""
    host = {
        "id": "host-1",
        "addresses": ["192.168.1.1", "host1.example.com"],
        "common_name": "host1",
        "principals": [
            {"principal": "root"},
            {"principal": "admin"},
        ],
    }
    entry = hosts_access_module._build_access_entry(
        user_id="user1",
        user_full_name="User One",
        principal="userone",
        source_name="Local",
        role_id="role1",
        role_name="admin-role",
        host=host,
    )
    assert entry["user_id"] == "user1"
    assert entry["user_name"] == "User One"
    assert entry["principal"] == "userone"
    assert entry["source_name"] == "Local"
    assert entry["role_id"] == "role1"
    assert entry["role_name"] == "admin-role"
    assert entry["target_host"] == "192.168.1.1,host1.example.com"
    assert entry["target_host_name"] == "host1"
    assert entry["target_host_id"] == "host-1"
    assert entry["target_accounts"] == "admin,root"


@pytest.mark.unit
def test_report_hosts_access_pagination(
    mock_report_api_user_hosts: MagicMock,
    mock_write_report_output: MagicMock,
    mock_output_config_user_hosts: dict,
    standard_csv_dir: str,
) -> None:
    """Test that report_hosts_access correctly handles paginated host fetching."""
    mock_api = MagicMock()
    mock_api.get_sources.return_value = MagicMock(ok=True, data={"items": [{"id": "source-1", "name": "Local"}]})
    mock_report_api_user_hosts.users.search_users.return_value = {
        "count": 1,
        "items": [
            {"id": "user123", "full_name": "user123", "principal": "userone", "source": "source-1"},
        ],
    }
    mock_report_api_user_hosts.get_user_roles.return_value = [
        {"id": "role1", "name": "admin-role"},
    ]

    def search_hosts_side_effect(api: object, search_payload: dict, offset: int, limit: int) -> dict[str, Any]:
        if offset == 0:
            return {
                "count": 150,
                "items": [
                    {
                        "id": f"host-{i}",
                        "addresses": [f"host{i}.example.com"],
                        "common_name": f"host{i}",
                        "principals": [
                            {
                                "principal": "root",
                                "roles": [{"id": "role1", "name": "admin-role"}],
                            },
                        ],
                    }
                    for i in range(100)
                ],
            }
        elif offset == 100:
            return {
                "count": 150,
                "items": [
                    {
                        "id": f"host-{i}",
                        "addresses": [f"host{i}.example.com"],
                        "common_name": f"host{i}",
                        "principals": [
                            {
                                "principal": "root",
                                "roles": [{"id": "role1", "name": "admin-role"}],
                            },
                        ],
                    }
                    for i in range(100, 150)
                ],
            }
        return {"count": 0, "items": []}

    mock_report_api_user_hosts.hosts.search_hosts.side_effect = search_hosts_side_effect
    inputs = HostsReportInputs(user_name="user123")
    report_ids = ReportIds(
        command="access",
        sub_command="hosts",
        report_prefix="access-hosts",
        config_key="access.subcommands.hosts",
    )
    result = hosts_access_module.report_hosts_access(
        mock_api,
        inputs,
        mock_output_config_user_hosts,
        report_ids,
        None,
    )
    assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}
    assert mock_report_api_user_hosts.hosts.search_hosts.call_count == 2
    mock_report_api_user_hosts.hosts.search_hosts.assert_any_call(mock_api, search_payload={}, offset=0, limit=100)
    mock_report_api_user_hosts.hosts.search_hosts.assert_any_call(mock_api, search_payload={}, offset=100, limit=100)


@pytest.mark.unit
def test_report_hosts_access_requires_search_option(
    mock_output_config_user_hosts: dict,
) -> None:
    """At least one of user_name, user_id, or principal is required."""
    mock_api = MagicMock()
    inputs = HostsReportInputs()
    report_ids = ReportIds(
        command="access",
        sub_command="hosts",
        report_prefix="access-hosts",
        config_key="access.subcommands.hosts",
    )

    result = hosts_access_module.report_hosts_access(
        mock_api,
        inputs,
        mock_output_config_user_hosts,
        report_ids,
        None,
    )

    assert result == {
        "report_path": None,
        "error_message": "At least one of --user-name, --user-id, or --principal is required",
        "info_message": None,
    }


@pytest.mark.unit
def test_report_hosts_access_to_map_requires_user_id(
    mock_report_api_user_hosts: MagicMock,
    mock_output_config_user_hosts: dict,
) -> None:
    """--to-map should be rejected unless --user-id is used."""
    mock_api = MagicMock()
    mock_api.get_sources.return_value = MagicMock(ok=True, data={"items": [{"id": "source-1", "name": "Local"}]})
    mock_report_api_user_hosts.users.search_users.return_value = {
        "count": 1,
        "items": [{"id": "user-1", "full_name": "User One", "principal": "user.one", "source": "source-1"}],
    }
    mock_report_api_user_hosts.get_user_roles.return_value = [{"id": "role-1", "name": "admin-role"}]
    mock_report_api_user_hosts.hosts.search_hosts.return_value = {
        "count": 1,
        "items": [
            {
                "id": "host-1",
                "addresses": ["host1.example.com"],
                "common_name": "host1",
                "principals": [{"principal": "root", "roles": [{"id": "role-1", "name": "admin-role"}]}],
            }
        ],
    }
    inputs = HostsReportInputs(user_name="User One", to_map=True)
    report_ids = ReportIds(
        command="access",
        sub_command="hosts",
        report_prefix="access-hosts",
        config_key="access.subcommands.hosts",
    )

    result = hosts_access_module.report_hosts_access(
        mock_api,
        inputs,
        mock_output_config_user_hosts,
        report_ids,
        None,
    )

    assert result == {
        "report_path": None,
        "error_message": "--to-map can only be used with --user-id",
        "info_message": None,
    }


@pytest.mark.unit
def test_report_hosts_access_to_map_with_user_id_prints_map(
    mock_report_api_user_hosts: MagicMock,
    mock_output_config_user_hosts: dict,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--to-map with --user-id should render and print the access tree."""
    mock_api = MagicMock()
    mock_api.get_sources.return_value = MagicMock(ok=True, data={"items": [{"id": "source-1", "name": "Local"}]})
    mock_report_api_user_hosts.users.get_user_by_id.return_value = {
        "id": "user-1",
        "full_name": "User One",
        "principal": "user.one",
        "source": "source-1",
    }
    mock_report_api_user_hosts.get_user_roles.return_value = [{"id": "role-1", "name": "admin-role"}]
    mock_report_api_user_hosts.hosts.search_hosts.return_value = {
        "count": 1,
        "items": [
            {
                "id": "host-1",
                "addresses": ["host1.example.com"],
                "common_name": "host1",
                "principals": [{"principal": "root", "roles": [{"id": "role-1", "name": "admin-role"}]}],
            }
        ],
    }
    inputs = HostsReportInputs(user_id="user-1", to_map=True)
    report_ids = ReportIds(
        command="access",
        sub_command="hosts",
        report_prefix="access-hosts",
        config_key="access.subcommands.hosts",
    )

    result = hosts_access_module.report_hosts_access(
        mock_api,
        inputs,
        mock_output_config_user_hosts,
        report_ids,
        None,
    )
    stdout = capsys.readouterr().out

    assert result == {"report_path": None, "error_message": None, "info_message": None}
    assert "Access Map: User -> Roles -> Hosts" in stdout
    assert "User One (user.one)" in stdout
    assert "admin-role" in stdout
    assert "host1" in stdout


@pytest.mark.unit
@patch("reports.access.hosts.report.resolve_allowed_access_group_ids")
def test_report_hosts_access_fails_when_access_group_name_unresolved(
    mock_resolve_allowed_access_group_ids: MagicMock,
    mock_report_api_user_hosts: MagicMock,
    mock_output_config_user_hosts: dict,
) -> None:
    """When user-group access-group names cannot be resolved, report should fail."""
    mock_api = MagicMock()
    mock_resolve_allowed_access_group_ids.return_value = (None, "Unknown access group")
    mock_api.get_sources.return_value = MagicMock(ok=True, data={"items": [{"id": "source-1", "name": "Local"}]})
    mock_report_api_user_hosts.users.search_users.return_value = {
        "count": 1,
        "items": [{"id": "user-1", "full_name": "User One", "principal": "user.one", "source": "source-1"}],
    }
    inputs = HostsReportInputs(user_name="User One")
    report_ids = ReportIds(
        command="access",
        sub_command="hosts",
        report_prefix="access-hosts",
        config_key="access.subcommands.hosts",
    )

    result = hosts_access_module.report_hosts_access(
        mock_api,
        inputs,
        mock_output_config_user_hosts,
        report_ids,
        None,
        user_group_id="11",
    )

    assert result == {
        "report_path": None,
        "error_message": "Unknown access group",
        "info_message": None,
    }
    mock_report_api_user_hosts.get_user_roles.assert_not_called()
