"""Shared fixtures for list secrets tests."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from lib.utils.config.report_ids import ReportIds


@pytest.fixture
def mock_output_config_secrets() -> dict:
    """Fixture for mock output configuration for secrets report."""
    return {
        "list": {
            "subcommands": {
                "secrets": {
                    "fields": {
                        "name": "true|Secret Name",
                        "read_roles": "true|Read Access Roles",
                        "write_roles": "true|Write Access Roles",
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_report_ids_secrets() -> ReportIds:
    """Fixture for mock report IDs for secrets report."""
    return ReportIds(
        command="list",
        sub_command="secrets",
        report_prefix="list-secrets",
        config_key="list.subcommands.secrets",
    )


@pytest.fixture
def mock_report_api_secrets() -> Generator[MagicMock]:
    """Fixture for mocking report API in secrets report."""
    from reports.list.secrets import report as secrets_module

    with patch.object(secrets_module, "report_api") as mock:
        yield mock


@pytest.fixture
def mock_env_config_secrets(standard_csv_dir: str) -> Generator[MagicMock]:
    """Fixture for mocking environment config in secrets report."""
    from lib.env import EnvConfig

    with patch.object(EnvConfig, "get_report_out_dir", return_value=standard_csv_dir):
        yield MagicMock()


@pytest.fixture
def mock_csv_writer_secrets(standard_csv_dir: str) -> Generator[MagicMock]:
    """Fixture for mocking CSV writer in secrets report."""
    from reports._shared import output as output_module

    with patch.object(output_module, "CsvWriter") as mock_class:
        mock_instance = MagicMock()
        mock_instance.write_to_file.return_value = standard_csv_dir
        mock_class.return_value = mock_instance
        yield mock_instance
