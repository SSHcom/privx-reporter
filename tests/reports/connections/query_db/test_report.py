"""Tests for query_db connections report."""

from unittest.mock import MagicMock, patch

import pytest

from reports.connections._shared.models import QueryReportInputs
from reports.connections.query_db.report import (
    _build_query,
    _fetch_connections,
    _validate_output_records,
    report_connections_db_query,
)


@pytest.mark.unit
def test_build_query_no_filters() -> None:
    """_build_query should create a basic query without filters."""
    inputs = QueryReportInputs(from_date="", to_date="")

    stmt = _build_query(inputs)

    result_str = str(stmt)
    assert "SELECT" in result_str
    assert "timestamp" in result_str


@pytest.mark.unit
@patch("reports.connections.query_db.report.validate_date")
def test_build_query_with_date_range(mock_validate_date: MagicMock) -> None:
    """_build_query should add timestamp filter for date range."""
    mock_validate_date.side_effect = [
        "2026-01-01T00:00:00.000000Z",
        "2026-01-10T23:59:59.999999Z",
    ]

    inputs = QueryReportInputs(from_date="2026-01-01", to_date="2026-01-10")

    stmt = _build_query(inputs)

    result_str = str(stmt)
    assert "timestamp >=" in result_str
    assert "timestamp <=" in result_str
    mock_validate_date.assert_called()


@pytest.mark.unit
def test_build_query_with_type_filter() -> None:
    """_build_query should add type filter with ILIKE."""
    inputs = QueryReportInputs(from_date="", to_date="", connection_type="SSH")

    stmt = _build_query(inputs)

    result_str = str(stmt)
    assert "data" in result_str
    assert "WHERE" in result_str
    assert "LIKE" in result_str


@pytest.mark.unit
def test_build_query_with_target_host_address_filter() -> None:
    """_build_query should add target_host_address filter with ILIKE."""
    inputs = QueryReportInputs(from_date="", to_date="", target_address="192.168.1.10")

    stmt = _build_query(inputs)

    result_str = str(stmt)
    assert "data" in result_str
    assert "WHERE" in result_str
    assert "LIKE" in result_str


@pytest.mark.unit
def test_build_query_with_target_host_account_filter() -> None:
    """_build_query should add target_host_account filter with ILIKE."""
    inputs = QueryReportInputs(from_date="", to_date="", target_account="root")

    stmt = _build_query(inputs)

    result_str = str(stmt)
    assert "data" in result_str
    assert "WHERE" in result_str
    assert "LIKE" in result_str


@pytest.mark.unit
def test_build_query_with_user_name_filter() -> None:
    """_build_query should add user_name filter with OR for full_name and principal."""
    inputs = QueryReportInputs(from_date="", to_date="", user_name="john")

    stmt = _build_query(inputs)

    result_str = str(stmt)
    assert "data" in result_str
    assert "WHERE" in result_str
    assert "OR" in result_str
    assert "LIKE" in result_str


@pytest.mark.unit
def test_build_query_orders_by_timestamp_desc() -> None:
    """_build_query should order by timestamp descending."""
    inputs = QueryReportInputs(from_date="", to_date="")

    stmt = _build_query(inputs)

    result_str = str(stmt)
    assert "order by" in result_str.lower()
    assert "timestamp" in result_str


@pytest.mark.unit
def test_build_query_with_access_group_filter() -> None:
    """_build_query should add access_group_id IN filter when provided."""
    inputs = QueryReportInputs(from_date="", to_date="")

    stmt = _build_query(inputs, allowed_access_group_ids={"ag-1", "ag-2"})

    result_str = str(stmt)
    assert "IN" in result_str
    assert "connection.data" in result_str
    compiled = stmt.compile()
    assert "access_group_id" in compiled.params.values()


@pytest.mark.unit
@patch("reports.connections.query_db.report.use_database")
def test_fetch_connections_empty_result(mock_use_database: MagicMock) -> None:
    """_fetch_connections should return empty list when no connections found."""
    inputs = QueryReportInputs(from_date="", to_date="")

    mock_db = MagicMock()
    mock_db.connection.execute.return_value.fetchall.return_value = []
    mock_use_database.return_value = mock_db

    result = _fetch_connections(inputs)

    assert result == []
    mock_db.connection.execute.assert_called_once()


@pytest.mark.unit
@patch("reports.connections.query_db.report.use_database")
def test_fetch_connections_with_data(mock_use_database: MagicMock) -> None:
    """_fetch_connections should return list of connection dicts."""
    inputs = QueryReportInputs(from_date="", to_date="")

    connection_data = {"id": "conn-1", "type": "SSH"}
    mock_result = [(connection_data,)]
    mock_db = MagicMock()
    mock_db.connection.execute.return_value.fetchall.return_value = mock_result
    mock_use_database.return_value = mock_db

    result = _fetch_connections(inputs)

    assert result == [connection_data]
    mock_db.connection.execute.assert_called_once()


@pytest.mark.unit
def test_validate_output_records_valid() -> None:
    """_validate_output_records should return None for valid records."""
    records = [
        {"connection_id": "conn-1", "type": "SSH"},
        {"connection_id": "conn-2", "type": "RDP"},
    ]
    field_names = ["connection_id", "type"]

    result = _validate_output_records(records, field_names)

    assert result is None


@pytest.mark.unit
def test_validate_output_records_missing_field() -> None:
    """_validate_output_records should return error message for missing field."""
    records = [
        {"connection_id": "conn-1"},
        {"connection_id": "conn-2", "type": "RDP"},
    ]
    field_names = ["connection_id", "type"]

    result = _validate_output_records(records, field_names)

    assert result is not None
    assert "validation failed" in result.lower()
    assert "conn-1" in result


@pytest.mark.unit
def test_validate_output_records_empty_list() -> None:
    """_validate_output_records should return None for empty list."""
    records = []
    field_names = ["connection_id", "type"]

    result = _validate_output_records(records, field_names)

    assert result is None


@pytest.mark.unit
@patch("reports.connections.query_db.report.write_report_output")
@patch("reports.connections.query_db.report.get_field_names_and_headers")
@patch("reports.connections.query_db.report._fetch_connections")
def test_report_connections_db_query_no_connections(
    mock_fetch_connections: MagicMock,
    mock_get_field_names_and_headers: MagicMock,
    mock_write_report_output: MagicMock,
    mock_api: MagicMock,
) -> None:
    """report_connections_db_query should return info message when no connections found."""
    mock_fetch_connections.return_value = []
    inputs = QueryReportInputs(from_date="2026-01-01", to_date="2026-01-10")
    output_config = {"connections": {"subcommands": {"query_db": {"fields": {"connection_id": "true|Connection ID"}}}}}
    from lib.utils.config.report_ids import ReportIds

    report_ids = ReportIds(
        command="connections",
        sub_command="query_db",
        report_prefix="connections-query-db",
        config_key="connections.subcommands.query_db",
    )

    result = report_connections_db_query(mock_api, inputs, output_config, report_ids)

    assert result["report_path"] is None
    assert result["error_message"] is None
    assert "No connections found" in result["info_message"]
    mock_write_report_output.assert_not_called()


@pytest.mark.unit
@patch("reports.connections.query_db.report.write_report_output")
@patch("reports.connections.query_db.report.get_field_names_and_headers")
@patch("reports.connections.query_db.report._fetch_connections")
def test_report_connections_db_query_validation_error(
    mock_fetch_connections: MagicMock,
    mock_get_field_names_and_headers: MagicMock,
    mock_write_report_output: MagicMock,
    mock_api: MagicMock,
) -> None:
    """report_connections_db_query should return error message when validation fails."""

    connection = {
        "id": "conn-1",
        "type": "SSH",
        "target_api_data": {},
        "target_network_data": {},
    }
    mock_fetch_connections.return_value = [connection]
    mock_get_field_names_and_headers.return_value = (
        ["connection_id", "nonexistent_field"],
        ["Connection ID", "Nonexistent Field"],
    )
    inputs = QueryReportInputs(from_date="2026-01-01", to_date="2026-01-10")
    output_config = {"connections": {"subcommands": {"query_db": {"fields": {"connection_id": "true|Connection ID"}}}}}
    from lib.utils.config.report_ids import ReportIds

    report_ids = ReportIds(
        command="connections",
        sub_command="query_db",
        report_prefix="connections-query-db",
        config_key="connections.subcommands.query_db",
    )

    result = report_connections_db_query(mock_api, inputs, output_config, report_ids)

    assert result["report_path"] is None
    assert result["error_message"] is not None
    assert "validation failed" in result["error_message"].lower()
    assert result["info_message"] is None
    mock_write_report_output.assert_not_called()


@pytest.mark.unit
@patch("reports.connections.query_db.report.write_report_output")
@patch("reports.connections.query_db.report.get_field_names_and_headers")
@patch("reports.connections.query_db.report._fetch_connections")
def test_report_connections_db_query_success(
    mock_fetch_connections: MagicMock,
    mock_get_field_names_and_headers: MagicMock,
    mock_write_report_output: MagicMock,
    mock_api: MagicMock,
) -> None:
    """report_connections_db_query should return successful report path."""
    connection = {
        "id": "conn-1",
        "type": "SSH",
        "created": "2026-01-02T10:00:00Z",
        "status": "TERMINATED",
        "target_api_data": {},
        "target_network_data": {},
    }
    mock_fetch_connections.return_value = [connection]
    mock_get_field_names_and_headers.return_value = (
        ["connection_id", "type", "created", "status"],
        ["Connection ID", "Type", "Created", "Status"],
    )
    mock_write_report_output.return_value = {
        "report_path": "/path/to/report.csv",
        "error_message": None,
        "info_message": None,
    }
    inputs = QueryReportInputs(from_date="2026-01-01", to_date="2026-01-10")
    output_config = {"connections": {"subcommands": {"query_db": {"fields": {"connection_id": "true|Connection ID"}}}}}
    from lib.utils.config.report_ids import ReportIds

    report_ids = ReportIds(
        command="connections",
        sub_command="query_db",
        report_prefix="connections-query-db",
        config_key="connections.subcommands.query_db",
    )

    result = report_connections_db_query(mock_api, inputs, output_config, report_ids)

    assert result["report_path"] is not None
    assert result["error_message"] is None
    assert result["info_message"] is None
    mock_write_report_output.assert_called_once()


@pytest.mark.unit
@patch("reports.connections.query_db.report.resolve_allowed_access_group_ids")
def test_report_connections_db_query_returns_error_for_unresolved_access_group(
    mock_resolve_allowed_access_group_ids: MagicMock,
    mock_api: MagicMock,
) -> None:
    """report_connections_db_query should fail when user-group access groups cannot be resolved."""
    mock_resolve_allowed_access_group_ids.return_value = (None, "Unknown access group")
    inputs = QueryReportInputs(from_date="2026-01-01", to_date="2026-01-10")
    output_config = {"connections": {"subcommands": {"query_db": {"fields": {"connection_id": "true|Connection ID"}}}}}
    from lib.utils.config.report_ids import ReportIds

    report_ids = ReportIds(
        command="connections",
        sub_command="query_db",
        report_prefix="connections-query-db",
        config_key="connections.subcommands.query_db",
    )

    result = report_connections_db_query(
        mock_api,
        inputs,
        output_config,
        report_ids,
        user_group_id="7",
    )

    assert result["report_path"] is None
    assert result["error_message"] == "Unknown access group"
    assert result["info_message"] is None


@pytest.mark.unit
@patch("reports.connections.query_db.report.write_report_output")
@patch("reports.connections.query_db.report.get_field_names_and_headers")
@patch("reports.connections.query_db.report._fetch_connections")
@patch("reports.connections.query_db.report.resolve_allowed_access_group_ids")
def test_report_connections_db_query_passes_allowed_access_groups_to_fetch(
    mock_resolve_allowed_access_group_ids: MagicMock,
    mock_fetch_connections: MagicMock,
    mock_get_field_names_and_headers: MagicMock,
    mock_write_report_output: MagicMock,
    mock_api: MagicMock,
) -> None:
    """report_connections_db_query should pass resolved access-group IDs to query fetch."""
    mock_resolve_allowed_access_group_ids.return_value = ({"ag-1"}, None)
    connection = {
        "id": "conn-1",
        "type": "SSH",
        "target_api_data": {},
        "target_network_data": {},
    }
    mock_fetch_connections.return_value = [connection]
    mock_get_field_names_and_headers.return_value = (
        ["connection_id"],
        ["Connection ID"],
    )
    mock_write_report_output.return_value = {
        "report_path": "/path/to/report.csv",
        "error_message": None,
        "info_message": None,
    }
    inputs = QueryReportInputs(from_date="2026-01-01", to_date="2026-01-10")
    output_config = {"connections": {"subcommands": {"query_db": {"fields": {"connection_id": "true|Connection ID"}}}}}
    from lib.utils.config.report_ids import ReportIds

    report_ids = ReportIds(
        command="connections",
        sub_command="query_db",
        report_prefix="connections-query-db",
        config_key="connections.subcommands.query_db",
    )

    report_connections_db_query(
        mock_api,
        inputs,
        output_config,
        report_ids,
        user_group_id="7",
    )

    mock_fetch_connections.assert_called_once_with(inputs, allowed_access_group_ids={"ag-1"})


@pytest.mark.unit
@patch("reports.connections.query_db.report.write_report_output")
@patch("reports.connections.query_db.report.get_field_names_and_headers")
@patch("reports.connections.query_db.report._fetch_connections")
def test_report_connections_db_query_with_requested_fields(
    mock_fetch_connections: MagicMock,
    mock_get_field_names_and_headers: MagicMock,
    mock_write_report_output: MagicMock,
    mock_api: MagicMock,
) -> None:
    """report_connections_db_query should use requested_fields when provided."""
    connection = {
        "id": "conn-1",
        "type": "SSH",
        "target_api_data": {},
        "target_network_data": {},
    }
    mock_fetch_connections.return_value = [connection]
    mock_get_field_names_and_headers.return_value = (
        ["connection_id"],
        ["Connection ID"],
    )
    mock_write_report_output.return_value = {
        "report_path": "/path/to/report.csv",
        "error_message": None,
        "info_message": None,
    }
    inputs = QueryReportInputs(from_date="2026-01-01", to_date="2026-01-10")
    output_config = {
        "connections": {
            "subcommands": {"query_db": {"fields": {"connection_id": "true|Connection ID", "type": "true|Type"}}}
        }
    }
    from lib.utils.config.report_ids import ReportIds

    report_ids = ReportIds(
        command="connections",
        sub_command="query_db",
        report_prefix="connections-query-db",
        config_key="connections.subcommands.query_db",
    )

    result = report_connections_db_query(
        mock_api, inputs, output_config, report_ids, requested_fields=["connection_id"]
    )

    assert result["report_path"] is not None
    mock_get_field_names_and_headers.assert_called_once_with(
        output_config, report_ids.config_key, requested_fields=["connection_id"]
    )
    mock_write_report_output.assert_called_once()
