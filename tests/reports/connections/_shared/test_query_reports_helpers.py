"""Tests for query reports helpers."""

import pytest

from reports.connections._shared.query_reports_helpers import extract_connection_fields


@pytest.mark.unit
def test_extract_connection_fields_basic() -> None:
    """extract_connection_fields should extract all fields correctly."""
    connection = {
        "id": "conn-1",
        "created": "2026-01-02T10:00:00Z",
        "connected": "2026-01-02T10:00:30Z",
        "disconnected": "2026-01-02T10:15:00Z",
        "duration": 870,
        "status": "TERMINATED",
        "type": "SSH",
        "user": {"id": "user-1"},
        "user_data": {"full_name": "John Doe", "principal": "john.doe"},
        "target_host": {"id": "host-1", "common_name": "server1.example.com"},
        "target_host_address": "192.168.1.10",
        "target_host_account": "root",
        "target_api_data": {"authorized_endpoints": []},
        "target_network_data": {"dst": []},
    }

    result = extract_connection_fields(connection)

    assert result == {
        "connection_id": "conn-1",
        "created": "2026-01-02T10:00:00Z",
        "connected": "2026-01-02T10:00:30Z",
        "disconnected": "2026-01-02T10:15:00Z",
        "duration": 870,
        "status": "TERMINATED",
        "type": "SSH",
        "authorized_endpoints": "",
        "user_id": "user-1",
        "user_name": "John Doe",
        "target_host_id": "host-1",
        "target_host_address": "192.168.1.10",
        "target_host_common_name": "server1.example.com",
        "target_host_account": "root",
        "target_ips": "",
    }


@pytest.mark.unit
def test_extract_connection_fields_with_principal_fallback() -> None:
    """user_name should fall back to principal if full_name is not available."""
    connection = {
        "id": "conn-1",
        "user": {"id": "user-1"},
        "user_data": {"principal": "jane.doe"},
        "target_api_data": {"authorized_endpoints": []},
        "target_network_data": {"dst": []},
    }

    result = extract_connection_fields(connection)
    assert result["user_name"] == "jane.doe"


@pytest.mark.unit
def test_extract_connection_fields_with_empty_user_data() -> None:
    """user_name should be empty string if user_data is empty."""
    connection = {
        "id": "conn-1",
        "user": {"id": "user-1"},
        "user_data": {},
        "target_api_data": {"authorized_endpoints": []},
        "target_network_data": {"dst": []},
    }

    result = extract_connection_fields(connection)
    assert result["user_name"] == ""


@pytest.mark.unit
def test_extract_connection_fields_with_multiple_authorized_endpoints() -> None:
    """Multiple authorized endpoints should be joined with quotes when comma present."""
    connection = {
        "id": "conn-1",
        "target_api_data": {
            "authorized_endpoints": [
                {"host": "host1.example.com"},
                {"host": "host2.example.com"},
            ]
        },
        "target_network_data": {"dst": []},
    }

    result = extract_connection_fields(connection)
    assert result["authorized_endpoints"] == '"host1.example.com, host2.example.com"'


@pytest.mark.unit
def test_extract_connection_fields_with_single_authorized_endpoint() -> None:
    """Single authorized endpoint should not have quotes."""
    connection = {
        "id": "conn-1",
        "target_api_data": {
            "authorized_endpoints": [
                {"host": "host1.example.com"},
            ]
        },
        "target_network_data": {"dst": []},
    }

    result = extract_connection_fields(connection)
    assert result["authorized_endpoints"] == "host1.example.com"


@pytest.mark.unit
def test_extract_connection_fields_with_empty_authorized_endpoints() -> None:
    """Empty authorized endpoints should result in empty string."""
    connection = {
        "id": "conn-1",
        "target_api_data": {"authorized_endpoints": []},
        "target_network_data": {"dst": []},
    }

    result = extract_connection_fields(connection)
    assert result["authorized_endpoints"] == ""


@pytest.mark.unit
def test_extract_connection_fields_with_none_authorized_endpoints() -> None:
    """None authorized endpoints should result in empty string."""
    connection = {
        "id": "conn-1",
        "target_api_data": {"authorized_endpoints": None},
        "target_network_data": {"dst": []},
    }

    result = extract_connection_fields(connection)
    assert result["authorized_endpoints"] == ""


@pytest.mark.unit
def test_extract_connection_fields_with_target_ips() -> None:
    """Target IPs should be extracted from dst list."""
    connection = {
        "id": "conn-1",
        "target_api_data": {"authorized_endpoints": []},
        "target_network_data": {
            "dst": [
                {"selector": {"ip": {"start": "192.168.1.10"}}},
                {"selector": {"ip": {"start": "192.168.1.20", "end": "192.168.1.30"}}},
            ]
        },
    }

    result = extract_connection_fields(connection)
    assert result["target_ips"] == "192.168.1.20-192.168.1.30, 192.168.1.10"


@pytest.mark.unit
def test_extract_connection_fields_with_missing_fields() -> None:
    """Missing fields should default to empty string."""
    connection = {
        "target_api_data": {},
        "target_network_data": {},
    }

    result = extract_connection_fields(connection)

    assert result["connection_id"] == ""
    assert result["created"] == ""
    assert result["connected"] == ""
    assert result["disconnected"] == ""
    assert result["duration"] == ""
    assert result["status"] == ""
    assert result["type"] == ""
    assert result["authorized_endpoints"] == ""
    assert result["user_id"] == ""
    assert result["user_name"] == ""
    assert result["target_host_id"] == ""
    assert result["target_host_address"] == ""
    assert result["target_host_common_name"] == ""
    assert result["target_host_account"] == ""
    assert result["target_ips"] == ""


@pytest.mark.unit
def test_extract_connection_fields_with_empty_user_dict() -> None:
    """Empty user dict should result in empty user_id."""
    connection = {
        "id": "conn-1",
        "user": {},
        "user_data": {"full_name": "John Doe"},
        "target_api_data": {"authorized_endpoints": []},
        "target_network_data": {"dst": []},
    }

    result = extract_connection_fields(connection)
    assert result["user_id"] == ""


@pytest.mark.unit
def test_extract_connection_fields_with_empty_target_host_dict() -> None:
    """Empty target_host dict should result in empty fields."""
    connection = {
        "id": "conn-1",
        "target_host": {},
        "target_api_data": {"authorized_endpoints": []},
        "target_network_data": {"dst": []},
    }

    result = extract_connection_fields(connection)
    assert result["target_host_id"] == ""
    assert result["target_host_common_name"] == ""


@pytest.mark.unit
def test_extract_connection_fields_with_missing_host_in_authorized_endpoints() -> None:
    """Endpoints without host field should be ignored."""
    connection = {
        "id": "conn-1",
        "target_api_data": {
            "authorized_endpoints": [
                {"host": "host1.example.com"},
                {"name": "endpoint2"},
                {"host": "host3.example.com"},
            ]
        },
        "target_network_data": {"dst": []},
    }

    result = extract_connection_fields(connection)
    assert result["authorized_endpoints"] == '"host1.example.com, host3.example.com"'


@pytest.mark.unit
def test_extract_connection_fields_full_name_takes_precedence_over_principal() -> None:
    """full_name should take precedence over principal for user_name."""
    connection = {
        "id": "conn-1",
        "user": {"id": "user-1"},
        "user_data": {"full_name": "John Doe", "principal": "john.doe"},
        "target_api_data": {"authorized_endpoints": []},
        "target_network_data": {"dst": []},
    }

    result = extract_connection_fields(connection)
    assert result["user_name"] == "John Doe"
