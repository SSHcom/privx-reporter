"""Shared fixtures for connections tests."""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lib.utils.config.report_ids import ReportIds
from reports.connections.details import report as connections_details_module


@pytest.fixture
def mock_date_validation() -> Generator[MagicMock]:
    """Fixture for mocking date validation."""
    with patch("reports.connections.query.report.validate_date") as mock:
        mock.side_effect = [
            "2026-01-01T00:00:00.000000Z",
            "2026-01-10T23:59:59.999999Z",
        ]
        yield mock


@pytest.fixture
def mock_env_config(standard_csv_dir: str, standard_batch_size: int) -> Generator[MagicMock]:
    """Fixture for mocking environment config."""
    with patch("reports.connections.query.report.EnvConfig") as mock:
        mock.get_api_batchsize.return_value = standard_batch_size
        yield mock


@pytest.fixture
def mock_report_api() -> Generator[MagicMock]:
    """Fixture for mocking report API."""
    with patch("reports.connections.query.report.report_api") as mock:
        yield mock


@pytest.fixture
def mock_env_config_details(standard_csv_dir: str) -> Generator[MagicMock]:
    """Fixture for mocking environment config in connections.details module."""
    with patch.object(connections_details_module, "EnvConfig") as mock:
        mock.get_report_out_dir.return_value = standard_csv_dir
        yield mock


@pytest.fixture
def mock_report_api_details() -> Generator[MagicMock]:
    """Fixture for mocking report API in connections.details module."""
    with patch.object(connections_details_module, "report_api") as mock:
        yield mock


@pytest.fixture
def mock_path_mkdir() -> Generator[MagicMock]:
    """Fixture for mocking Path.mkdir to avoid filesystem operations."""
    with patch("pathlib.Path.mkdir") as mock:
        yield mock


@pytest.fixture
def sample_connection() -> dict[str, Any]:
    """Fixture providing a sample connection object."""
    return {
        "id": "conn-1",
        "created": "2026-01-02T10:00:00Z",
        "connected": "2026-01-02T10:00:30Z",
        "disconnected": "2026-01-02T10:15:00Z",
        "duration": 870,
        "status": "TERMINATED",
        "type": "SSH",
        "user": {"id": "user-1", "display_name": "John Doe"},
        "user_data": {"full_name": "John Doe", "principal": "john.doe"},
        "target_host": {"id": "host-1", "common_name": "server1.example.com"},
        "target_host_address": "192.168.1.10",
        "target_host_account": "root",
        "target_api_data": {},
    }


@pytest.fixture
def sample_connections(sample_connection: dict[str, Any]) -> list[dict[str, Any]]:
    """Fixture providing multiple sample connections."""
    return [
        sample_connection,
        {
            "id": "conn-2",
            "created": "2026-01-05T14:00:00Z",
            "connected": "2026-01-05T14:00:15Z",
            "disconnected": "2026-01-05T14:30:00Z",
            "duration": 1785,
            "status": "TERMINATED",
            "type": "RDP",
            "user": {"id": "user-2", "display_name": "Jane Smith"},
            "user_data": {"full_name": "Jane Smith", "principal": "jane.smith"},
            "target_host": {"id": "host-2", "common_name": "server2.example.com"},
            "target_host_address": "192.168.1.20",
            "target_host_account": "admin",
            "target_api_data": {},
        },
    ]


@pytest.fixture
def mock_output_config_query() -> dict[str, Any]:
    """Fixture for mock output configuration for connections query report."""
    return {
        "connections": {
            "subcommands": {
                "query": {
                    "fields": {
                        "connection_id": "true|Connection ID",
                        "created": "true|Created",
                        "connected": "true|Connected",
                        "disconnected": "true|Disconnected",
                        "duration": "true|Duration",
                        "status": "true|Status",
                        "type": "true|Type",
                        "authorized_endpoints": "true|Authorized Endpoints",
                        "user_id": "true|User ID",
                        "user_name": "true|User Name",
                        "target_host_id": "true|Target Host ID",
                        "target_host_address": "true|Target Host Address",
                        "target_host_common_name": "true|Target Host Common Name",
                        "target_host_account": "true|Target Host Account",
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_report_ids() -> ReportIds:
    """Fixture for mock report IDs."""
    return ReportIds(
        command="connections",
        sub_command="query",
        report_prefix="connections-query",
        config_key="connections.subcommands.query",
    )


@pytest.fixture
def mock_report_ids_details() -> ReportIds:
    """Fixture for mock report IDs for details."""
    return ReportIds(
        command="connections",
        sub_command="details",
        report_prefix="connections-details",
        config_key="connections.subcommands.details",
    )


@pytest.fixture
def mock_output_config_details() -> dict[str, Any]:
    """Fixture for mock output configuration for connections details report."""
    return {
        "connections": {
            "subcommands": {
                "details": {
                    "fields": {
                        "connection_id": "true|Connection ID",
                        "created": "true|Created",
                        "connected": "true|Connected",
                        "disconnected": "true|Disconnected",
                        "duration": "true|Duration",
                        "status": "true|Status",
                        "type": "true|Type",
                        "authorized_endpoints": "true|Authorized Endpoints",
                        "user_id": "true|User ID",
                        "user_name": "true|User Name",
                        "user_display_name": "true|User Display Name",
                        "target_host_id": "true|Target Host ID",
                        "target_host_address": "true|Target Host Address",
                        "target_host_common_name": "true|Target Host Common Name",
                        "target_host_account": "true|Target Host Account",
                    }
                }
            }
        }
    }
