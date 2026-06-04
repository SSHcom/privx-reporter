"""Tests for connection details report function."""

from unittest.mock import MagicMock, patch

import pytest

from reports.connections._shared.models import DetailsReportInputs
from reports.connections.details import report as connection_details_module


@pytest.fixture
def sample_connection_data() -> dict:
    """Fixture providing sample connection data."""
    return {
        "id": "conn-1",
        "created": "2026-01-02T10:00:00Z",
        "connected": "2026-01-02T10:00:30Z",
        "disconnected": "2026-01-02T10:15:00Z",
        "duration": 870,
        "status": "TERMINATED",
        "type": "SSH",
        "user": {"id": "user-1", "display_name": "John Doe"},
        "target_host": {"id": "host-1", "common_name": "server1.example.com"},
        "target_host_address": "192.168.1.10",
        "target_host_account": "root",
        "target_api_data": {},
    }


@pytest.fixture
def sample_connection_with_missing_fields() -> dict:
    """Fixture providing connection data with missing fields."""
    return {
        "id": "conn-1",
        "type": "SSH",
        "user": {},
        "target_host": {},
    }


@pytest.mark.unit
def test_report_connection_details_csv_success(
    mock_api: MagicMock,
    mock_report_api_details: MagicMock,
    mock_env_config_details: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    standard_csv_dir: str,
    sample_connection_data: dict,
    mock_output_config_details: dict,
    mock_report_ids_details: dict,
) -> None:
    """Test connection details are correctly retrieved and written to CSV."""
    connection_id = "conn-1"
    mock_report_api_details.get_connection.return_value = sample_connection_data

    # Mock get_user_by_id for user lookup
    mock_report_api_details.get_user_by_id.return_value = {
        "id": "user-1",
        "full_name": "John Doe Full",
        "principal": "john.doe",
    }

    # Mock write_report_output
    with patch.object(connection_details_module, "write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": f"{standard_csv_dir}/connections-details-{connection_id}.csv",
            "error_message": None,
            "info_message": None,
        }

        result = connection_details_module.report_connection_details(
            mock_api,
            DetailsReportInputs(connection_id=connection_id),
            mock_output_config_details,
            mock_report_ids_details,
        )

    mock_report_api_details.get_connection.assert_called_once_with(mock_api, connection_id)

    # Verify write_report_output was called
    assert mock_write.called
    call_args = mock_write.call_args
    assert call_args[0][0] == f"connections-details.{connection_id}"

    # Verify the output data
    output_data = call_args[0][4]
    assert len(output_data) == 1
    data = output_data[0]
    assert data["connection_id"] == "conn-1"
    assert data["user_id"] == "user-1"
    assert data["user_name"] == "John Doe Full"
    assert data["user_display_name"] == "John Doe"
    assert data["target_host_id"] == "host-1"
    assert data["target_host_common_name"] == "server1.example.com"
    assert data["target_host_account"] == "root"
    assert data["target_host_address"] == "192.168.1.10"

    # Verify result
    assert result["report_path"] == f"{standard_csv_dir}/connections-details-{connection_id}.csv"
    assert result["error_message"] is None


@pytest.mark.unit
def test_report_connection_details_json_success(
    mock_api: MagicMock,
    mock_report_api_details: MagicMock,
    mock_env_config_details: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    standard_csv_dir: str,
    sample_connection_data: dict,
    mock_output_config_details: dict,
    mock_report_ids_details: dict,
) -> None:
    """Test connection details are correctly retrieved and written to JSON."""
    connection_id = "conn-1"
    mock_report_api_details.get_connection.return_value = sample_connection_data

    # Mock get_user_by_id for user lookup
    mock_report_api_details.get_user_by_id.return_value = {
        "id": "user-1",
        "full_name": "John Doe Full",
        "principal": "john.doe",
    }

    # Mock write_report_output
    with patch.object(connection_details_module, "write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": f"{standard_csv_dir}/connections-details-{connection_id}.json",
            "error_message": None,
            "info_message": None,
        }

        connection_details_module.report_connection_details(
            mock_api,
            DetailsReportInputs(connection_id=connection_id, to_json=True),
            mock_output_config_details,
            mock_report_ids_details,
        )

    mock_report_api_details.get_connection.assert_called_once_with(mock_api, connection_id)

    # Verify write_report_output was called with to_json=True
    assert mock_write.called
    call_args = mock_write.call_args
    assert call_args[0][1].to_json is True  # to_json is in inputs (position 1)

    # Verify the output data structure
    output_data = call_args[0][4]
    assert isinstance(output_data, list)
    assert len(output_data) == 1
    connection_data = output_data[0]

    assert connection_data["connection_id"] == "conn-1"
    assert connection_data["user_id"] == "user-1"
    assert connection_data["user_name"] == "John Doe Full"
    assert connection_data["user_display_name"] == "John Doe"
    assert connection_data["target_host_id"] == "host-1"


@pytest.mark.unit
def test_report_connection_details_no_data(
    mock_api: MagicMock,
    mock_report_api_details: MagicMock,
    mock_env_config_details: MagicMock,  # noqa
    mock_output_config_details: dict,
    mock_report_ids_details: dict,
) -> None:
    """Test report_connection_details when no connection data is returned."""
    connection_id = "conn-1"
    mock_report_api_details.get_connection.return_value = None

    result = connection_details_module.report_connection_details(
        mock_api,
        DetailsReportInputs(connection_id=connection_id),
        mock_output_config_details,
        mock_report_ids_details,
    )

    mock_report_api_details.get_connection.assert_called_once_with(mock_api, connection_id)

    # Verify result indicates no data found
    assert result["report_path"] is None
    assert result["error_message"] is None
    assert result["info_message"] is not None
    assert "No connection data returned" in result["info_message"]


@pytest.mark.unit
def test_report_connection_details_missing_fields(
    mock_api: MagicMock,
    mock_report_api_details: MagicMock,
    mock_env_config_details: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    sample_connection_with_missing_fields: dict,
    mock_output_config_details: dict,
    mock_report_ids_details: dict,
) -> None:
    """Test connection details with missing fields are handled with empty strings."""
    connection_id = "conn-1"
    mock_report_api_details.get_connection.return_value = sample_connection_with_missing_fields

    # Mock get_user_by_id to fail (user not found)
    mock_report_api_details.get_user_by_id.side_effect = Exception("User not found")

    # Mock write_report_output
    with patch.object(connection_details_module, "write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": "/path/to/report.csv",
            "error_message": None,
            "info_message": None,
        }

        connection_details_module.report_connection_details(
            mock_api,
            DetailsReportInputs(connection_id=connection_id),
            mock_output_config_details,
            mock_report_ids_details,
        )

    # Verify write_report_output was called
    assert mock_write.called
    call_args = mock_write.call_args
    output_data = call_args[0][4]
    assert len(output_data) == 1
    output = output_data[0]

    assert output["connection_id"] == "conn-1"
    assert output["type"] == "SSH"
    assert output["created"] == ""
    assert output["connected"] == ""
    assert output["disconnected"] == ""
    assert output["duration"] == ""
    assert output["status"] == ""
    assert output["user_id"] == ""
    assert output["user_name"] == ""  # Failed user lookup
    assert output["user_display_name"] == ""
    assert output["target_host_id"] == ""
    assert output["target_host_common_name"] == ""
    assert output["target_host_account"] == ""
    assert output["target_host_address"] == ""
    assert output["authorized_endpoints"] == ""  # Empty when target_api_data is missing


@pytest.mark.unit
def test_report_connection_details_api_with_authorized_endpoints(
    mock_api: MagicMock,
    mock_report_api_details: MagicMock,
    mock_env_config_details: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    mock_output_config_details: dict,
    mock_report_ids_details: dict,
) -> None:
    """Test that authorized_endpoints are correctly extracted for API connections."""
    connection_id = "conn-api-1"

    api_connection_data = {
        "id": connection_id,
        "created": "2026-01-02T10:00:00Z",
        "connected": "2026-01-02T10:00:30Z",
        "disconnected": "2026-01-02T10:15:00Z",
        "duration": 870,
        "status": "TERMINATED",
        "type": "API",
        "user": {"id": "user-1", "display_name": "John Doe"},
        "target_host": {"id": "host-1", "common_name": "k8s-api"},
        "target_host_address": "k8s-api",
        "target_host_account": "",
        "target_api_data": {
            "id": "api-1",
            "name": "k8s-api",
            "authorized_endpoints": [
                {
                    "host": "cluster1.example.com:443",
                    "protocols": ["*"],
                    "methods": ["*"],
                    "paths": ["**"],
                },
                {
                    "host": "cluster2.example.com:443",
                    "protocols": ["*"],
                    "methods": ["*"],
                    "paths": ["**"],
                },
            ],
        },
    }

    mock_report_api_details.get_connection.return_value = api_connection_data

    # Mock get_user_by_id for user lookup
    mock_report_api_details.get_user_by_id.return_value = {
        "id": "user-1",
        "full_name": "John Doe",
        "principal": "john.doe",
    }

    # Mock write_report_output
    with patch.object(connection_details_module, "write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": f"/path/to/connections-details-{connection_id}.csv",
            "error_message": None,
            "info_message": None,
        }

        connection_details_module.report_connection_details(
            mock_api,
            DetailsReportInputs(connection_id=connection_id),
            mock_output_config_details,
            mock_report_ids_details,
        )

    # Verify write_report_output was called
    assert mock_write.called
    call_args = mock_write.call_args
    output_data = call_args[0][4]
    assert len(output_data) == 1
    data = output_data[0]

    # Verify authorized_endpoints are formatted as CSV
    assert data["connection_id"] == connection_id
    assert data["type"] == "API"
    assert data["authorized_endpoints"] == "cluster1.example.com:443, cluster2.example.com:443"


@pytest.mark.unit
def test_report_connection_details_api_with_none_authorized_endpoints(
    mock_api: MagicMock,
    mock_report_api_details: MagicMock,
    mock_env_config_details: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    mock_output_config_details: dict,
    mock_report_ids_details: dict,
) -> None:
    """Test that None authorized_endpoints are handled correctly."""
    connection_id = "conn-api-2"

    api_connection_data = {
        "id": connection_id,
        "type": "API",
        "user": {"id": "user-1", "display_name": "John Doe"},
        "target_host": {"id": "host-1", "common_name": "k8s-api"},
        "target_api_data": {
            "id": "api-1",
            "name": "k8s-api",
            "authorized_endpoints": None,  # Explicitly None
        },
    }

    mock_report_api_details.get_connection.return_value = api_connection_data

    # Mock get_user_by_id for user lookup
    mock_report_api_details.get_user_by_id.return_value = {
        "id": "user-1",
        "full_name": "John Doe",
        "principal": "john.doe",
    }

    # Mock write_report_output
    with patch.object(connection_details_module, "write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": f"/path/to/connections-details-{connection_id}.csv",
            "error_message": None,
            "info_message": None,
        }

        connection_details_module.report_connection_details(
            mock_api,
            DetailsReportInputs(connection_id=connection_id),
            mock_output_config_details,
            mock_report_ids_details,
        )

    # Verify write_report_output was called
    assert mock_write.called
    call_args = mock_write.call_args
    output_data = call_args[0][4]
    assert len(output_data) == 1
    data = output_data[0]

    # Verify authorized_endpoints is empty string when None
    assert data["connection_id"] == connection_id
    assert data["authorized_endpoints"] == ""


@pytest.mark.unit
def test_report_connection_details_filters_by_user_group_denied(
    mock_api: MagicMock,
    mock_report_api_details: MagicMock,
    mock_env_config_details: MagicMock,  # noqa
    sample_connection_data: dict,
    mock_output_config_details: dict,
    mock_report_ids_details: dict,
) -> None:
    connection_id = "conn-1"
    sample_connection_data["access_group_id"] = "ag-denied"
    mock_report_api_details.get_connection.return_value = sample_connection_data

    with patch.object(
        connection_details_module,
        "resolve_allowed_access_group_ids",
        return_value=({"ag-allowed"}, None),
    ):
        result = connection_details_module.report_connection_details(
            mock_api,
            DetailsReportInputs(connection_id=connection_id),
            mock_output_config_details,
            mock_report_ids_details,
            user_group_id="10",
        )

    assert result["report_path"] is None
    assert result["error_message"] is None
    assert "No connection data returned" in (result["info_message"] or "")


@pytest.mark.unit
def test_report_connection_details_filters_by_user_group_allowed(
    mock_api: MagicMock,
    mock_report_api_details: MagicMock,
    mock_env_config_details: MagicMock,  # noqa
    sample_connection_data: dict,
    mock_output_config_details: dict,
    mock_report_ids_details: dict,
) -> None:
    connection_id = "conn-1"
    sample_connection_data["target_host"] = {"id": "host-1", "common_name": "server1.example.com"}
    sample_connection_data.pop("access_group_id", None)
    mock_report_api_details.get_connection.return_value = sample_connection_data
    mock_report_api_details.hosts.get_host.return_value = {"id": "host-1", "access_group_id": "ag-allowed"}
    mock_report_api_details.get_user_by_id.return_value = {"id": "user-1", "full_name": "John Doe Full"}

    with (
        patch.object(
            connection_details_module,
            "resolve_allowed_access_group_ids",
            return_value=({"ag-allowed"}, None),
        ),
        patch.object(connection_details_module, "write_report_output") as mock_write,
    ):
        mock_write.return_value = {"report_path": "/tmp/details.csv", "error_message": None, "info_message": None}
        result = connection_details_module.report_connection_details(
            mock_api,
            DetailsReportInputs(connection_id=connection_id),
            mock_output_config_details,
            mock_report_ids_details,
            user_group_id="10",
        )

    assert result["error_message"] is None
    mock_report_api_details.hosts.get_host.assert_called_once_with(mock_api, "host-1")
    assert mock_write.called


@pytest.mark.unit
def test_report_connection_details_json_source_ignores_output_config(
    mock_api: MagicMock,
    mock_report_api_details: MagicMock,
    sample_connection_data: dict,
    mock_report_ids_details: dict,
) -> None:
    mock_report_api_details.get_connection.return_value = sample_connection_data

    with patch.object(connection_details_module, "JsonWriter") as mock_json_writer:
        mock_json_writer.return_value.write_to_file.return_value = "/tmp/details-source.json"
        result = connection_details_module.report_connection_details(
            mock_api,
            DetailsReportInputs(connection_id="conn-1", json_source=True),
            output_config={},
            report_ids=mock_report_ids_details,
        )

    assert result == {"report_path": "/tmp/details-source.json", "error_message": None, "info_message": None}


@pytest.mark.unit
def test_report_connection_details_empty_output_config_returns_error(
    mock_api: MagicMock,
    mock_report_api_details: MagicMock,
    sample_connection_data: dict,
    mock_report_ids_details: dict,
) -> None:
    mock_report_api_details.get_connection.return_value = sample_connection_data

    result = connection_details_module.report_connection_details(
        mock_api,
        DetailsReportInputs(connection_id="conn-1"),
        output_config={},
        report_ids=mock_report_ids_details,
    )

    assert result["report_path"] is None
    assert "Output configuration is required for connections details report" in (result["error_message"] or "")
    assert result["info_message"] is None


@pytest.mark.unit
def test_report_connection_details_output_validation_failure(
    mock_api: MagicMock,
    mock_report_api_details: MagicMock,
    sample_connection_data: dict,
    mock_output_config_details: dict,
    mock_report_ids_details: dict,
) -> None:
    mock_report_api_details.get_connection.return_value = sample_connection_data
    mock_report_api_details.get_user_by_id.return_value = {
        "id": "user-1",
        "full_name": "John Doe",
    }

    with patch.object(
        connection_details_module,
        "get_field_names_and_headers",
        return_value=(["missing_field"], ["Missing"]),
    ):
        result = connection_details_module.report_connection_details(
            mock_api,
            DetailsReportInputs(connection_id="conn-1"),
            mock_output_config_details,
            mock_report_ids_details,
        )

    assert result["report_path"] is None
    assert "Output configuration validation failed for connection" in (result["error_message"] or "")
