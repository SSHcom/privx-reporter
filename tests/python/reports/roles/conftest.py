"""Shared fixtures for roles tests."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from lib.utils.config.report_ids import ReportIds


@pytest.fixture
def mock_report_api() -> Generator[MagicMock]:
    """Fixture for mocking report API in roles.query module."""
    from reports.roles.query import report as roles_query_module

    with patch.object(roles_query_module, "report_api") as mock:
        yield mock


@pytest.fixture
def mock_env_config(standard_csv_dir: str, standard_batch_size: int) -> Generator[MagicMock]:
    """Fixture for mocking environment config in roles.list module."""
    from lib.env import EnvConfig

    with (
        patch.object(EnvConfig, "get_report_out_dir", return_value=standard_csv_dir),
        patch.object(EnvConfig, "get_api_batchsize", return_value=standard_batch_size),
    ):
        yield MagicMock()


@pytest.fixture
def mock_csv_writer(standard_csv_dir: str) -> Generator[MagicMock]:
    """Fixture for mocking CSV writer in roles.list module."""
    from reports._shared import output as output_module

    with patch.object(output_module, "CsvWriter") as mock_class:
        mock_instance = MagicMock()
        mock_instance.write_to_file.return_value = standard_csv_dir
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_report_api_user() -> Generator[MagicMock]:
    """Fixture for mocking report API in roles.user module."""
    from reports.roles.user import report as roles_user_module

    with patch.object(roles_user_module, "report_api") as mock:
        yield mock


@pytest.fixture
def mock_env_config_user(standard_csv_dir: str, standard_batch_size: int) -> Generator[MagicMock]:
    """Fixture for mocking environment config in roles.user module."""
    from lib.env import EnvConfig

    with (
        patch.object(EnvConfig, "get_report_out_dir", return_value=standard_csv_dir),
        patch.object(EnvConfig, "get_api_batchsize", return_value=standard_batch_size),
    ):
        yield MagicMock()


@pytest.fixture
def mock_csv_writer_user(standard_csv_dir: str) -> Generator[MagicMock]:
    """Fixture for mocking CSV writer in roles.user module."""
    from reports._shared import output as output_module

    with patch.object(output_module, "CsvWriter") as mock_class:
        mock_instance = MagicMock()
        mock_instance.write_to_file.return_value = standard_csv_dir
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_report_api_members() -> Generator[MagicMock]:
    """Fixture for mocking report API in roles.members module."""
    from reports.roles.members import report as roles_members_module

    with patch.object(roles_members_module, "report_api") as mock:
        yield mock


@pytest.fixture
def mock_env_config_members(standard_csv_dir: str, standard_batch_size: int) -> Generator[MagicMock]:
    """Fixture for mocking environment config in roles.members module."""
    from lib.env import EnvConfig

    with (
        patch.object(EnvConfig, "get_report_out_dir", return_value=standard_csv_dir),
        patch.object(EnvConfig, "get_api_batchsize", return_value=standard_batch_size),
    ):
        yield MagicMock()


@pytest.fixture
def mock_csv_writer_members(standard_csv_dir: str) -> Generator[MagicMock]:
    """Fixture for mocking CSV writer in roles.members module."""
    from reports._shared import output as output_module

    with patch.object(output_module, "CsvWriter") as mock_class:
        mock_instance = MagicMock()
        mock_instance.write_to_file.return_value = standard_csv_dir
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_report_api_context_restrict() -> Generator[MagicMock]:
    """Fixture for mocking report API in roles.restrictions module."""
    from reports.roles.restrictions import report as roles_restrictions_module

    with patch.object(roles_restrictions_module, "report_api") as mock:
        yield mock


@pytest.fixture
def mock_env_config_context_restrict(standard_csv_dir: str, standard_batch_size: int) -> Generator[MagicMock]:
    """Fixture for mocking environment config in roles.restrictions module."""
    from lib.env import EnvConfig

    with (
        patch.object(EnvConfig, "get_report_out_dir", return_value=standard_csv_dir),
        patch.object(EnvConfig, "get_api_batchsize", return_value=standard_batch_size),
    ):
        yield MagicMock()


@pytest.fixture
def mock_csv_writer_context_restrict(standard_csv_dir: str) -> Generator[MagicMock]:
    """Fixture for mocking CSV writer in roles.restrictions module."""
    from reports._shared import output as output_module

    with patch.object(output_module, "CsvWriter") as mock_class:
        mock_instance = MagicMock()
        mock_instance.write_to_file.return_value = standard_csv_dir
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_report_ids() -> ReportIds:
    """Fixture for mock report IDs for roles query."""
    return ReportIds(
        command="roles",
        sub_command="query",
        report_prefix="roles-list",
        config_key="roles.subcommands.query",
    )


@pytest.fixture
def mock_report_ids_members() -> ReportIds:
    """Fixture for mock report IDs for roles members."""
    return ReportIds(
        command="roles",
        sub_command="members",
        report_prefix="role-members",
        config_key="roles.subcommands.members",
    )


@pytest.fixture
def mock_report_ids_user() -> ReportIds:
    """Fixture for mock report IDs for roles user."""
    return ReportIds(
        command="roles",
        sub_command="user",
        report_prefix="roles-user",
        config_key="roles.subcommands.user",
    )


@pytest.fixture
def mock_output_config_all() -> dict:
    """Fixture for mock output configuration for roles query report."""
    return {
        "roles": {
            "subcommands": {
                "query": {
                    "fields": {
                        "role_id": "false|Role ID",
                        "role_name": "true|Role Name",
                        "block_role": "true|Block Role",
                        "validity": "true|Validity",
                        "start_time": "true|Start Time",
                        "end_time": "true|End Time",
                        "timezone": "true|Timezone",
                        "ip_masks": "true|IP Masks",
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_output_config_members() -> dict:
    """Fixture for mock output configuration for roles members report."""
    return {
        "roles": {
            "subcommands": {
                "members": {
                    "fields": {
                        "role_name": "true|Role Name",
                        "principal": "true|Principal",
                        "full_name": "true|Full Name",
                        "email": "true|Email",
                        "samaccountname": "true|SAM Account Name",
                        "windows_account": "true|Windows Account",
                        "unix_account": "true|Unix Account",
                        "source_type": "true|Source Type",
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_output_config_user() -> dict:
    """Fixture for mock output configuration for roles user report."""
    return {
        "roles": {
            "subcommands": {
                "user": {
                    "fields": {
                        "user_id": "false|User ID",
                        "role_id": "false|Role ID",
                        "role_name": "true|Role Name",
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_output_config_context_restrict() -> dict:
    """Fixture for mock output configuration for roles restrictions report."""
    return {
        "roles": {
            "subcommands": {
                "restrictions": {
                    "fields": {
                        "role_id": "false|Role ID",
                        "role_name": "true|Role Name",
                        "block_role": "true|Block Role",
                        "validity": "true|Validity",
                        "start_time": "true|Start Time",
                        "end_time": "true|End Time",
                        "timezone": "true|Timezone",
                        "ip_masks": "true|IP Masks",
                    }
                }
            }
        }
    }
