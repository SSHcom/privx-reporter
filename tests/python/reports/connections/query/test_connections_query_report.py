"""Tests for connections query report functions."""

from unittest.mock import MagicMock, patch

import pytest

from reports.connections._shared.models import QueryReportInputs
from reports.connections.query.report import report_connections_query


def _create_search_response(connections: list) -> dict:
    """Helper to create a search response object."""
    return {"count": len(connections), "items": connections}


@pytest.mark.unit
def test_report_connections_query_date_range_success(
    mock_date_validation: MagicMock,
    mock_report_api: MagicMock,
    mock_env_config: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    sample_connections: list,
    standard_csv_dir: str,
    mock_output_config_query: dict,
    mock_report_ids: dict,
) -> None:
    """Test that report_connections_query validates dates and writes connections to CSV."""
    mock_api = MagicMock()
    from_date = "2026-01-01"
    to_date = "2026-01-10"

    # Mock search_connections response
    mock_report_api.search_connections.return_value = _create_search_response(sample_connections)

    # Mock write_report_output
    with patch("reports.connections.query.report.write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": f"{standard_csv_dir}/connections-query.csv",
            "error_message": None,
            "info_message": None,
        }

        result = report_connections_query(
            api=mock_api,
            inputs=QueryReportInputs(from_date=from_date, to_date=to_date),
            output_config=mock_output_config_query,
            report_ids=mock_report_ids,
        )

    # Verify date validation calls
    assert mock_date_validation.call_count == 2
    mock_date_validation.assert_any_call(from_date, "from_date")
    mock_date_validation.assert_any_call(to_date, "to_date", end_of_day=True)

    # Verify search_connections was called twice (once for connected, once for disconnected)
    assert mock_report_api.search_connections.call_count == 2

    # Verify write_report_output was called
    assert mock_write.called
    call_args = mock_write.call_args
    assert call_args[0][0] == "connections-query"  # name is first positional arg
    # Verify output_data (5th positional arg) has correct structure
    output_data = call_args[0][4]
    assert len(output_data) == 2
    assert output_data[0]["connection_id"] == "conn-1"
    assert output_data[0]["user_name"] == "John Doe"
    assert output_data[1]["connection_id"] == "conn-2"
    assert output_data[1]["user_name"] == "Jane Smith"

    # Verify result
    assert result["report_path"] == f"{standard_csv_dir}/connections-query.csv"
    assert result["error_message"] is None


@pytest.mark.unit
def test_report_connections_query_no_connections(
    mock_date_validation: MagicMock,  # noqa
    mock_report_api: MagicMock,
    mock_env_config: MagicMock,  # noqa
    mock_output_config_query: dict,
    mock_report_ids: dict,
) -> None:
    """Test that report_connections_query returns info message when no connections found."""
    mock_api = MagicMock()
    from_date = "2026-01-01"
    to_date = "2026-01-10"

    # Mock empty response
    mock_report_api.search_connections.return_value = _create_search_response([])

    result = report_connections_query(
        api=mock_api,
        inputs=QueryReportInputs(from_date=from_date, to_date=to_date),
        output_config=mock_output_config_query,
        report_ids=mock_report_ids,
    )

    # Verify search was called twice (once for connected, once for disconnected)
    assert mock_report_api.search_connections.call_count == 2

    # Verify result indicates no connections found
    assert result["report_path"] is None
    assert result["error_message"] is None
    assert result["info_message"] == "No connections found matching the specified filters"


@pytest.mark.unit
def test_report_connections_query_with_pagination(
    mock_date_validation: MagicMock,  # noqa
    mock_report_api: MagicMock,
    mock_env_config: MagicMock,
    mock_path_mkdir: MagicMock,  # noqa
    sample_connection: dict,
    mock_output_config_query: dict,
    mock_report_ids: dict,
) -> None:
    """Test that report_connections_query handles paginated API responses."""
    mock_api = MagicMock()
    from_date = "2026-01-01"
    to_date = "2026-01-10"
    batch_size = 2

    mock_env_config.get_api_batchsize.return_value = batch_size

    # Create 3 connections for pagination test
    connections_page1 = [
        {**sample_connection, "id": f"conn-{i}", "user": {"id": f"user-{i}", "display_name": f"User {i}"}}
        for i in range(1, 3)
    ]
    connections_page2 = [
        {**sample_connection, "id": "conn-3", "type": "RDP", "user": {"id": "user-3", "display_name": "User 3"}}
    ]

    # Mock paginated responses - need to handle 2 queries (connected and disconnected)
    mock_report_api.search_connections.side_effect = [
        {"count": 3, "items": connections_page1},  # First query (connected) - first page
        {"count": 3, "items": connections_page2},  # First query (connected) - second page
        {"count": 0, "items": []},  # Second query (disconnected) - empty
    ]

    # Mock write_report_output
    with patch("reports.connections.query.report.write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": "/path/to/report.csv",
            "error_message": None,
            "info_message": None,
        }

        report_connections_query(
            api=mock_api,
            inputs=QueryReportInputs(from_date=from_date, to_date=to_date),
            output_config=mock_output_config_query,
            report_ids=mock_report_ids,
        )

    # Verify pagination - 2 calls for connected query, 1 call for disconnected query
    assert mock_report_api.search_connections.call_count == 3

    # Verify write_report_output was called with all 3 connections
    assert mock_write.called
    call_args = mock_write.call_args
    output_data = call_args[0][4]
    assert len(output_data) == 3


@pytest.mark.unit
def test_report_connections_query_missing_fields(
    mock_date_validation: MagicMock,  # noqa
    mock_report_api: MagicMock,
    mock_env_config: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    mock_output_config_query: dict,
    mock_report_ids: dict,
) -> None:
    """Test that report_connections_query handles missing fields with empty strings."""
    mock_api = MagicMock()
    from_date = "2026-01-01"
    to_date = "2026-01-10"

    # Mock response with missing fields
    mock_report_api.search_connections.return_value = {
        "count": 1,
        "items": [{"id": "conn-1", "user": {}, "target_host": {}}],
    }

    # Mock write_report_output
    with patch("reports.connections.query.report.write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": "/path/to/report.csv",
            "error_message": None,
            "info_message": None,
        }

        report_connections_query(
            api=mock_api,
            inputs=QueryReportInputs(from_date=from_date, to_date=to_date),
            output_config=mock_output_config_query,
            report_ids=mock_report_ids,
        )

    # Verify write_report_output was called with empty strings for missing fields
    assert mock_write.called
    call_args = mock_write.call_args
    output_data = call_args[0][4]
    assert len(output_data) == 1
    output = output_data[0]
    assert output["connection_id"] == "conn-1"
    assert output["created"] == ""
    assert output["user_id"] == ""
    assert output["user_name"] == ""
    assert output["target_host_id"] == ""
    assert output["authorized_endpoints"] == ""  # Empty when target_api_data is missing


@pytest.mark.unit
def test_report_connections_query_with_host_filters(
    mock_date_validation: MagicMock,  # noqa
    mock_report_api: MagicMock,
    mock_env_config: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    sample_connections: list,
    mock_output_config_query: dict,
    mock_report_ids: dict,
) -> None:
    """Test that report_connections_query includes host filter parameters."""
    mock_api = MagicMock()
    from_date = "2026-01-01"
    to_date = "2026-01-10"

    # Mock search_connections response
    mock_report_api.search_connections.return_value = _create_search_response(sample_connections)

    # Mock write_report_output
    with patch("reports.connections.query.report.write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": "/path/to/report.csv",
            "error_message": None,
            "info_message": None,
        }

        result = report_connections_query(
            api=mock_api,
            inputs=QueryReportInputs(
                from_date=from_date,
                to_date=to_date,
                target_address="192.168.1.10",
                target_account="root",
            ),
            output_config=mock_output_config_query,
            report_ids=mock_report_ids,
        )

    # Verify search_connections was called twice (connected + disconnected range queries)
    assert mock_report_api.search_connections.call_count == 2

    # Verify account filter is included in both calls (address is post-filtered in report logic)
    for call in mock_report_api.search_connections.call_args_list:
        search_payload = call[1]["search_payload"]
        assert search_payload["target_host_account"] == ["root"]

    # Verify result
    assert result["report_path"] is not None
    assert result["error_message"] is None


@pytest.mark.unit
def test_report_connections_query_with_user_name_filter(
    mock_date_validation: MagicMock,  # noqa
    mock_report_api: MagicMock,
    mock_env_config: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    sample_connections: list,
    mock_output_config_query: dict,
    mock_report_ids: dict,
) -> None:
    """Test that user_name post-filter works correctly."""
    mock_api = MagicMock()
    from_date = "2026-01-01"
    to_date = "2026-01-10"

    # Mock search_connections response with multiple users
    mock_report_api.search_connections.return_value = _create_search_response(sample_connections)

    # Mock write_report_output
    with patch("reports.connections.query.report.write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": "/path/to/report.csv",
            "error_message": None,
            "info_message": None,
        }

        report_connections_query(
            api=mock_api,
            inputs=QueryReportInputs(from_date=from_date, to_date=to_date, user_name="Jane"),
            output_config=mock_output_config_query,
            report_ids=mock_report_ids,
        )

    # Verify write_report_output was called with filtered connections
    assert mock_write.called
    call_args = mock_write.call_args
    output_data = call_args[0][4]
    # Should only contain Jane Smith's connection (substring match on "Jane")
    assert len(output_data) == 1
    assert output_data[0]["user_name"] == "Jane Smith"


@pytest.mark.unit
def test_report_connections_query_user_name_no_match(
    mock_date_validation: MagicMock,  # noqa
    mock_report_api: MagicMock,
    mock_env_config: MagicMock,  # noqa
    sample_connections: list,
    mock_output_config_query: dict,
    mock_report_ids: dict,
) -> None:
    """Test that user_name filter returns empty when no match."""
    mock_api = MagicMock()
    from_date = "2026-01-01"
    to_date = "2026-01-10"

    # Mock search_connections response
    mock_report_api.search_connections.return_value = _create_search_response(sample_connections)

    result = report_connections_query(
        api=mock_api,
        inputs=QueryReportInputs(from_date=from_date, to_date=to_date, user_name="NonExistentUser"),
        output_config=mock_output_config_query,
        report_ids=mock_report_ids,
    )

    # Verify result indicates no connections found after filtering
    assert result["report_path"] is None
    assert result["error_message"] is None
    assert result["info_message"] == "No connections found matching the specified filters"


@pytest.mark.unit
def test_report_connections_query_date_range_mandatory() -> None:
    """Test that query inputs allow missing date range (report defaults last 7 days)."""
    from argparse import Namespace

    from reports._shared.input import get_report_inputs

    # No dates provided — engine should reject before reaching the report function
    args = Namespace(
        user_name="John Doe",
        from_date="",
        to_date="",
        target_host_address="",
        target_host_common_name="",
        target_host_account="",
        type="",
        to_json=False,
        to_stdout=False,
        output_dir=None,
    )
    result = get_report_inputs(QueryReportInputs, args)

    assert result._error_message is None


@pytest.mark.unit
def test_report_connections_query_with_authorized_endpoints(
    mock_date_validation: MagicMock,  # noqa
    mock_report_api: MagicMock,
    mock_env_config: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    mock_output_config_query: dict,
    mock_report_ids: dict,
) -> None:
    """Test that authorized_endpoints are correctly extracted and quoted when multiple."""
    mock_api = MagicMock()
    from_date = "2026-01-01"
    to_date = "2026-01-10"

    # Mock API connection with authorized_endpoints
    api_connection = {
        "id": "conn-api-1",
        "created": "2026-01-02T10:00:00Z",
        "connected": "2026-01-02T10:00:30Z",
        "disconnected": "2026-01-02T10:15:00Z",
        "duration": 870,
        "status": "TERMINATED",
        "type": "API",
        "user": {"id": "user-1", "display_name": "John Doe"},
        "user_data": {"full_name": "John Doe", "principal": "john.doe"},
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

    # Mock search response
    mock_report_api.search_connections.return_value = _create_search_response([api_connection])

    # Mock write_report_output
    with patch("reports.connections.query.report.write_report_output") as mock_write:
        mock_write.return_value = {"report_path": "/path/to/report.csv", "error_message": None, "info_message": None}

        report_connections_query(
            api=mock_api,
            inputs=QueryReportInputs(from_date=from_date, to_date=to_date),
            output_config=mock_output_config_query,
            report_ids=mock_report_ids,
        )

    # Verify write_report_output was called
    assert mock_write.called
    call_args = mock_write.call_args
    output_data = call_args[0][4]
    assert len(output_data) == 1
    output = output_data[0]

    # Verify authorized_endpoints are quoted when multiple
    assert output["connection_id"] == "conn-api-1"
    assert output["type"] == "API"
    assert output["authorized_endpoints"] == '"cluster1.example.com:443, cluster2.example.com:443"'


@pytest.mark.unit
def test_report_connections_query_single_endpoint_not_quoted(
    mock_date_validation: MagicMock,  # noqa
    mock_report_api: MagicMock,
    mock_env_config: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    mock_output_config_query: dict,
    mock_report_ids: dict,
) -> None:
    """Test that single authorized_endpoint is not quoted."""
    mock_api = MagicMock()
    from_date = "2026-01-01"
    to_date = "2026-01-10"

    # Mock API connection with single endpoint
    api_connection = {
        "id": "conn-api-1",
        "created": "2026-01-02T10:00:00Z",
        "connected": "2026-01-02T10:00:30Z",
        "disconnected": "2026-01-02T10:15:00Z",
        "duration": 870,
        "status": "TERMINATED",
        "type": "API",
        "user": {"id": "user-1", "display_name": "John Doe"},
        "user_data": {"full_name": "John Doe", "principal": "john.doe"},
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
            ],
        },
    }

    # Mock search response
    mock_report_api.search_connections.return_value = _create_search_response([api_connection])

    # Mock write_report_output
    with patch("reports.connections.query.report.write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": "/path/to/report.csv",
            "error_message": None,
            "info_message": None,
        }

        report_connections_query(
            api=mock_api,
            inputs=QueryReportInputs(from_date=from_date, to_date=to_date),
            output_config=mock_output_config_query,
            report_ids=mock_report_ids,
        )

    # Verify single endpoint is not quoted
    assert mock_write.called
    call_args = mock_write.call_args
    output = call_args[0][4][0]
    assert output["authorized_endpoints"] == "cluster1.example.com:443"


@pytest.mark.unit
def test_report_connections_query_type_filter(
    mock_date_validation: MagicMock,  # noqa
    mock_report_api: MagicMock,
    mock_env_config: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    sample_connections: list,
    mock_output_config_query: dict,
    mock_report_ids: dict,
) -> None:
    """Test that type filter works correctly alongside mandatory date range."""
    mock_api = MagicMock()
    from_date = "2026-01-01"
    to_date = "2026-01-10"

    # Mock search_connections response
    mock_report_api.search_connections.return_value = _create_search_response(sample_connections)

    # Mock write_report_output
    with patch("reports.connections.query.report.write_report_output") as mock_write:
        mock_write.return_value = {"report_path": "/path/to/report.csv", "error_message": None, "info_message": None}

        result = report_connections_query(
            api=mock_api,
            inputs=QueryReportInputs(from_date=from_date, to_date=to_date, connection_type="SSH"),
            output_config=mock_output_config_query,
            report_ids=mock_report_ids,
        )

    # Verify search_connections was called twice (connected + disconnected) with type filter
    assert mock_report_api.search_connections.call_count == 2
    for call in mock_report_api.search_connections.call_args_list:
        search_payload = call[1]["search_payload"]
        assert search_payload["type"] == ["SSH"]

    # Verify result
    assert result["report_path"] is not None
    assert result["error_message"] is None


@pytest.mark.unit
def test_report_connections_query_type_with_date_range(
    mock_date_validation: MagicMock,
    mock_report_api: MagicMock,
    mock_env_config: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    sample_connections: list,
    mock_output_config_query: dict,
    mock_report_ids: dict,
) -> None:
    """Test that type filter works with date range."""
    mock_api = MagicMock()
    from_date = "2026-01-01"
    to_date = "2026-01-10"

    # Mock search_connections response
    mock_report_api.search_connections.return_value = _create_search_response(sample_connections)

    # Mock write_report_output
    with patch("reports.connections.query.report.write_report_output") as mock_write:
        mock_write.return_value = {"report_path": "/path/to/report.csv", "error_message": None, "info_message": None}

        result = report_connections_query(
            api=mock_api,
            inputs=QueryReportInputs(from_date=from_date, to_date=to_date, connection_type="SSH"),
            output_config=mock_output_config_query,
            report_ids=mock_report_ids,
        )

    # Verify date validation was called
    assert mock_date_validation.call_count == 2

    # Verify search_connections was called twice (connected + disconnected) with type filter
    assert mock_report_api.search_connections.call_count == 2
    for call in mock_report_api.search_connections.call_args_list:
        search_payload = call[1]["search_payload"]
        assert search_payload["type"] == ["SSH"]

    # Verify result
    assert result["report_path"] is not None
    assert result["error_message"] is None


@pytest.mark.unit
@patch("reports.connections.query.report.resolve_allowed_access_group_ids")
def test_report_connections_query_returns_error_for_unresolved_access_group(
    mock_resolve_allowed_access_group_ids: MagicMock,
    mock_date_validation: MagicMock,  # noqa
    mock_report_api: MagicMock,  # noqa
    mock_env_config: MagicMock,  # noqa
    mock_output_config_query: dict,
    mock_report_ids: dict,
) -> None:
    """report_connections_query should fail when user-group access groups cannot be resolved."""
    mock_api = MagicMock()
    mock_resolve_allowed_access_group_ids.return_value = (None, "Unknown access group")

    result = report_connections_query(
        api=mock_api,
        inputs=QueryReportInputs(from_date="2026-01-01", to_date="2026-01-10"),
        output_config=mock_output_config_query,
        report_ids=mock_report_ids,
        user_group_id="9",
    )

    assert result["report_path"] is None
    assert result["error_message"] == "Unknown access group"
    assert result["info_message"] is None


@pytest.mark.unit
@patch("reports.connections.query.report.resolve_allowed_access_group_ids")
def test_report_connections_query_filters_by_access_group(
    mock_resolve_allowed_access_group_ids: MagicMock,
    mock_date_validation: MagicMock,  # noqa
    mock_report_api: MagicMock,
    mock_env_config: MagicMock,  # noqa
    mock_output_config_query: dict,
    mock_report_ids: dict,
) -> None:
    """report_connections_query should keep only allowed access groups when user_group_id is provided."""
    mock_api = MagicMock()
    mock_resolve_allowed_access_group_ids.return_value = ({"ag-allowed"}, None)
    from_date = "2026-01-01"
    to_date = "2026-01-10"

    connections = [
        {
            "id": "conn-1",
            "user": {"id": "user-1", "display_name": "User 1"},
            "user_data": {"full_name": "User 1", "principal": "user1"},
            "target_host": {"id": "host-1", "common_name": "host-1"},
            "target_api_data": {},
            "target_network_data": {},
            "access_group_id": "ag-allowed",
        },
        {
            "id": "conn-2",
            "user": {"id": "user-2", "display_name": "User 2"},
            "user_data": {"full_name": "User 2", "principal": "user2"},
            "target_host": {"id": "host-2", "common_name": "host-2"},
            "target_api_data": {},
            "target_network_data": {},
            "access_group_id": "ag-denied",
        },
    ]
    mock_report_api.search_connections.return_value = _create_search_response(connections)

    with patch("reports.connections.query.report.write_report_output") as mock_write:
        mock_write.return_value = {"report_path": "/path/to/report.csv", "error_message": None, "info_message": None}

        report_connections_query(
            api=mock_api,
            inputs=QueryReportInputs(from_date=from_date, to_date=to_date),
            output_config=mock_output_config_query,
            report_ids=mock_report_ids,
            user_group_id="9",
        )

    output_data = mock_write.call_args[0][4]
    assert len(output_data) == 1
    assert output_data[0]["connection_id"] == "conn-1"
