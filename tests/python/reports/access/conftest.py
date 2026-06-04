"""Shared fixtures for access tests."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from lib.utils.config.report_ids import ReportIds


# Output config fixtures
@pytest.fixture
def mock_output_config_host_account() -> dict:
    """Fixture for mock output configuration for host account access report."""
    return {
        "access": {
            "subcommands": {
                "account": {
                    "fields": {
                        "user_name": "true|User Name",
                        "role_name": "true|Role Name",
                        "target_host": "true|Target Host",
                        "target_account": "true|Target Account",
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_output_config_host_user_restrict() -> dict:
    """Fixture for mock output configuration for host user restrict report."""
    return {
        "access": {
            "subcommands": {
                "account-restrictions": {
                    "fields": {
                        "target_host_id": "true|Host ID",
                        "target_host": "true|Target Host",
                        "account_name": "true|Account Name",
                        "default_whitelist_name": "true|Default Whitelist Name",
                        "whitelist_names": "true|Whitelist Names",
                        "allow_no_match": "true|Allow No Match",
                        "audit_match": "true|Audit Match",
                        "audit_no_match": "true|Audit No Match",
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_output_config_user_access() -> dict:
    """Fixture for mock output configuration for user access map report."""
    return {
        "access": {
            "subcommands": {
                "role-map": {
                    "fields": {
                        "user_id": "true|User ID",
                        "role_name": "true|Role Name",
                        "target_host": "true|Target Host",
                        "target_accounts": "true|Target Accounts",
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_output_config_user_hosts() -> dict:
    """Fixture for mock output configuration for user hosts access report."""
    return {
        "access": {
            "subcommands": {
                "hosts": {
                    "fields": {
                        "user_id": "true|User ID",
                        "role_name": "true|Role Name",
                        "target_host": "true|Target Host",
                        "target_accounts": "true|Target Accounts",
                    }
                }
            }
        }
    }


# Fixtures for account_restrictions module
@pytest.fixture
def mock_report_api_hosts() -> Generator[MagicMock]:
    """Fixture for mocking report API hosts module."""
    from reports.access._shared import helpers as helpers_module
    from reports.access.account_restrictions import report as account_restrictions_module

    with (
        patch.object(account_restrictions_module, "report_api") as mock1,
        patch.object(helpers_module, "report_api") as mock2,
    ):
        # Make both mocks return the same responses
        mock2.get_role_members = mock1.get_role_members
        yield mock1


@pytest.fixture
def mock_env_config_hosts(standard_csv_dir: str, standard_batch_size: int) -> Generator[MagicMock]:
    """Fixture for mocking environment config in account_restrictions module."""
    from lib.env import EnvConfig

    with (
        patch.object(EnvConfig, "get_report_out_dir", return_value=standard_csv_dir),
        patch.object(EnvConfig, "get_api_batchsize", return_value=standard_batch_size),
    ):
        yield MagicMock()


@pytest.fixture
def mock_csv_writer_hosts(standard_csv_dir: str) -> Generator[MagicMock]:
    """Fixture for mocking CSV writer in account_restrictions module."""
    from reports._shared import output as output_module

    with patch.object(output_module, "CsvWriter") as mock_class:
        mock_instance = MagicMock()
        mock_instance.write_to_file.return_value = standard_csv_dir
        mock_class.return_value = mock_instance
        yield mock_instance


# Fixtures for host_map module
@pytest.fixture
def mock_report_api_user_access() -> Generator[MagicMock]:
    """Fixture for mocking report API in host_map module."""
    from reports.access._shared import helpers as helpers_module
    from reports.access.role_map import report as host_map_module

    with patch.object(host_map_module, "report_api") as mock1, patch.object(helpers_module, "report_api") as mock2:
        # Make both mocks return same responses
        mock2.get_role_members = mock1.get_role_members
        yield mock1


@pytest.fixture
def mock_env_config_user_access(standard_csv_dir: str, standard_batch_size: int) -> Generator[MagicMock]:
    """Fixture for mocking environment config in host_map module."""
    from lib.env import EnvConfig

    with (
        patch.object(EnvConfig, "get_report_out_dir", return_value=standard_csv_dir),
        patch.object(EnvConfig, "get_api_batchsize", return_value=standard_batch_size),
    ):
        yield MagicMock()


@pytest.fixture
def mock_csv_writer_user_access(standard_csv_dir: str) -> Generator[MagicMock]:
    """Fixture for mocking CSV writer in host_map module."""
    from reports._shared import output as output_module

    with patch.object(output_module, "CsvWriter") as mock_class:
        mock_instance = MagicMock()
        mock_instance.write_to_file.return_value = standard_csv_dir
        mock_class.return_value = mock_instance
        yield mock_instance


# Fixtures for account_access module
@pytest.fixture
def mock_report_api_host_account() -> Generator[MagicMock]:
    """Fixture for mocking report API in account_access module."""
    from reports.access._shared import helpers as helpers_module
    from reports.access.account import report as account_access_module

    with (
        patch.object(account_access_module, "report_api") as mock1,
        patch.object(helpers_module, "report_api") as mock2,
    ):
        # Make both mocks return the same responses
        mock2.get_role_members = mock1.get_role_members
        yield mock1


@pytest.fixture
def mock_env_config_host_account(standard_csv_dir: str, standard_batch_size: int) -> Generator[MagicMock]:
    """Fixture for mocking environment config in account_access module."""
    from lib.env import EnvConfig

    with (
        patch.object(EnvConfig, "get_report_out_dir", return_value=standard_csv_dir),
        patch.object(EnvConfig, "get_api_batchsize", return_value=standard_batch_size),
    ):
        yield MagicMock()


@pytest.fixture
def mock_csv_writer_host_account(standard_csv_dir: str) -> Generator[MagicMock]:
    """Fixture for mocking CSV writer in account_access module."""
    from reports._shared import output as output_module

    with patch.object(output_module, "CsvWriter") as mock_class:
        mock_instance = MagicMock()
        mock_instance.write_to_file.return_value = standard_csv_dir
        mock_class.return_value = mock_instance
        yield mock_instance


# Fixtures for hosts_access module
@pytest.fixture
def mock_report_api_user_hosts() -> Generator[MagicMock]:
    """Fixture for mocking report API in hosts_access module."""
    from reports.access.hosts import report as hosts_access_module

    with patch.object(hosts_access_module, "report_api") as mock:
        yield mock


@pytest.fixture
def mock_env_config_user_hosts(standard_csv_dir: str, standard_batch_size: int) -> Generator[MagicMock]:
    """Fixture for mocking environment config in hosts_access module."""
    from lib.env import EnvConfig

    with (
        patch.object(EnvConfig, "get_report_out_dir", return_value=standard_csv_dir),
        patch.object(EnvConfig, "get_api_batchsize", return_value=standard_batch_size),
    ):
        yield MagicMock()


@pytest.fixture
def mock_csv_writer_user_hosts(standard_csv_dir: str) -> Generator[MagicMock]:
    """Fixture for mocking CSV writer in hosts_access module."""
    from reports._shared import output as output_module

    with patch.object(output_module, "CsvWriter") as mock_class:
        mock_instance = MagicMock()
        mock_instance.write_to_file.return_value = standard_csv_dir
        mock_class.return_value = mock_instance
        yield mock_instance


# Fixtures for access_query module
@pytest.fixture
def mock_report_api_access_query() -> Generator[MagicMock]:
    """Fixture for mocking report API in access_query module."""
    from reports.access._shared import helpers as helpers_module
    from reports.access.query import report as access_query_module

    with patch.object(access_query_module, "report_api") as mock1, patch.object(helpers_module, "report_api") as mock2:
        # Make both mocks return the same responses
        mock2.get_role_members = mock1.get_role_members
        yield mock1


@pytest.fixture
def mock_env_config_access_query(standard_csv_dir: str, standard_batch_size: int) -> Generator[MagicMock]:
    """Fixture for mocking environment config in access_query module."""
    from lib.env import EnvConfig

    with patch.object(EnvConfig, "get_api_batchsize", return_value=standard_batch_size):
        yield MagicMock()


@pytest.fixture
def mock_path_mkdir() -> Generator[MagicMock]:
    """Fixture for mocking Path.mkdir to avoid filesystem operations."""
    from pathlib import Path

    with patch.object(Path, "mkdir") as mock:
        yield mock


@pytest.fixture
def mock_json_debug_dumps() -> Generator[MagicMock]:
    """Fixture for mocking json.dump debug writes in access query report."""
    import json

    with (
        patch("reports.access.query.report.open", create=True),
        patch.object(json, "dump"),
    ):
        yield MagicMock()


@pytest.fixture
def sample_host() -> dict:
    """Fixture providing a sample host object."""
    return {
        "id": "host-1",
        "addresses": ["server1.example.com", "192.168.1.10"],
        "common_name": "server1",
        "access_group_id": "ag-1",
        "services": [
            {"service": "SSH"},
            {"service": "RDP"},
        ],
        "principals": [
            {
                "principal": "root",
                "roles": [{"id": "role-1", "name": "admin-role"}],
            },
            {
                "principal": "admin",
                "roles": [{"id": "role-1", "name": "admin-role"}],
            },
        ],
        "tags": ["production", "linux"],
    }


@pytest.fixture
def sample_hosts(sample_host: dict) -> list[dict]:
    """Fixture providing multiple sample hosts."""
    return [
        sample_host,
        {
            "id": "host-2",
            "addresses": ["server2.example.com", "192.168.1.20"],
            "common_name": "server2",
            "access_group_id": "ag-2",
            "services": [
                {"service": "SSH"},
            ],
            "principals": [
                {
                    "principal": "ubuntu",
                    "roles": [{"id": "role-2", "name": "user-role"}],
                }
            ],
            "tags": ["staging", "linux"],
        },
    ]


@pytest.fixture
def mock_output_config_access_query() -> dict:
    """Fixture for mock output configuration for access query report."""
    return {
        "access": {
            "subcommands": {
                "query": {
                    "fields": {
                        "user_id": "true|User ID",
                        "user_name": "true|User Name",
                        "role_id": "true|Role ID",
                        "role_name": "true|Role Name",
                        "target_host": "true|Target Host",
                        "target_host_id": "true|Target Host ID",
                        "target_account": "true|Target Account",
                        "host_common_name": "true|Host Common Name",
                        "access_group_id": "true|Access Group ID",
                        "access_group_name": "true|Access Group Name",
                        "access_group_comment": "true|Access Group Comment",
                        "access_group_default": "true|Access Group Default",
                        "service_type": "true|Service Type",
                        "tags": "true|Tags",
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_report_ids_access_query() -> ReportIds:
    """Fixture for mock report IDs for access query."""
    return ReportIds(
        command="access",
        sub_command="query",
        report_prefix="access-query",
        config_key="access.subcommands.query",
    )
