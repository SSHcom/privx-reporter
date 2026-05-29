"""Tests for access query report functions."""

from unittest.mock import MagicMock, patch

import pytest

from reports.access._shared.models import QueryReportInputs
from reports.access.query import report as query_report_module
from reports.access.query.report import report_access_query


def _create_search_response(hosts: list) -> dict:
    """Helper to create a search response object."""
    return {"count": len(hosts), "items": hosts}


@pytest.mark.unit
def test_report_access_query_host_address_success(
    mock_report_api_access_query: MagicMock,
    mock_env_config_access_query: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    mock_json_debug_dumps: MagicMock,  # noqa
    sample_hosts: list,
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    """Test that report_access_query searches hosts by address and writes CSV."""
    mock_api = MagicMock()

    mock_report_api_access_query.hosts.search_hosts.return_value = _create_search_response(sample_hosts)

    mock_report_api_access_query.get_role_members.return_value = {
        "count": 2,
        "items": [
            {"id": "user1", "full_name": "John Doe"},
            {"id": "user2", "full_name": "Jane Smith"},
        ],
    }

    with patch("reports.access.query.report.write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": "/test/report_out/access-query.csv",
            "error_message": None,
            "info_message": None,
        }

        inputs = QueryReportInputs(target_address="server1.example.com")
        result = report_access_query(
            api=mock_api,
            inputs=inputs,
            output_config=mock_output_config_access_query,
            report_ids=mock_report_ids_access_query,
            requested_fields=None,
        )

    assert result["report_path"] == "/test/report_out/access-query.csv"
    assert result["error_message"] is None
    mock_report_api_access_query.hosts.search_hosts.assert_called_once()
    call_args = mock_report_api_access_query.hosts.search_hosts.call_args
    search_payload = call_args[0][1]
    assert search_payload["keywords"] == "server1.example.com"


@pytest.mark.unit
def test_report_access_query_no_hosts_found(
    mock_report_api_access_query: MagicMock,
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    """Test that report_access_query returns info message when no hosts found."""
    mock_api = MagicMock()

    mock_report_api_access_query.hosts.search_hosts.return_value = _create_search_response([])

    inputs = QueryReportInputs(target_address="nonexistent.example.com")
    result = report_access_query(
        api=mock_api,
        inputs=inputs,
        output_config=mock_output_config_access_query,
        report_ids=mock_report_ids_access_query,
        requested_fields=None,
    )

    assert result["report_path"] is None
    assert result["error_message"] is None
    assert result["info_message"] == "No hosts found matching the specified search criteria"


@pytest.mark.unit
def test_report_access_query_no_filters_rejected(
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    """Test that no filters at all is rejected."""
    mock_api = MagicMock()

    inputs = QueryReportInputs()
    result = report_access_query(
        api=mock_api,
        inputs=inputs,
        output_config=mock_output_config_access_query,
        report_ids=mock_report_ids_access_query,
        requested_fields=None,
    )

    assert result["report_path"] is None
    assert "At least one filter is required" in result["error_message"]
    assert result["info_message"] is None


@pytest.mark.unit
def test_report_access_query_user_name_alone_rejected(
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    """Test that user_name alone is rejected without other filters."""
    mock_api = MagicMock()

    inputs = QueryReportInputs(user_name="John Doe")
    result = report_access_query(
        api=mock_api,
        inputs=inputs,
        output_config=mock_output_config_access_query,
        report_ids=mock_report_ids_access_query,
        requested_fields=None,
    )

    assert result["report_path"] is None
    assert "'user-name'" in result["error_message"]
    assert result["info_message"] is None


@pytest.mark.unit
def test_report_access_query_access_group_filter(
    mock_report_api_access_query: MagicMock,
    mock_env_config_access_query: MagicMock,
    mock_path_mkdir: MagicMock,  # noqa
    mock_json_debug_dumps: MagicMock,  # noqa
    sample_hosts: list,
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    """Test that access_group_name filter resolves IDs and searches correctly."""
    mock_api = MagicMock()

    mock_report_api_access_query.search_access_groups.return_value = {
        "count": 1,
        "items": [{"id": "ag-1", "name": "Production Access", "comment": ""}],
    }
    mock_report_api_access_query.hosts.search_hosts.return_value = _create_search_response(sample_hosts)

    mock_report_api_access_query.get_role_members.return_value = {
        "count": 2,
        "items": [
            {"id": "user1", "full_name": "John Doe"},
            {"id": "user2", "full_name": "Jane Smith"},
        ],
    }

    with patch("reports.access.query.report.write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": "/test/report_out/access-query.csv",
            "error_message": None,
            "info_message": None,
        }

        inputs = QueryReportInputs(access_group_name="Production")
        result = report_access_query(
            api=mock_api,
            inputs=inputs,
            output_config=mock_output_config_access_query,
            report_ids=mock_report_ids_access_query,
            requested_fields=None,
        )

    assert result["report_path"] is not None
    assert result["error_message"] is None
    mock_report_api_access_query.search_access_groups.assert_called_once()
    mock_report_api_access_query.hosts.search_hosts.assert_called_once()
    call_args = mock_report_api_access_query.hosts.search_hosts.call_args
    search_payload = call_args[0][1]
    assert "access_group_ids" in search_payload
    assert search_payload["access_group_ids"] == ["ag-1"]


@pytest.mark.unit
def test_report_access_query_access_group_not_found(
    mock_report_api_access_query: MagicMock,
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    """Test that non-matching access group returns info message."""
    mock_api = MagicMock()

    mock_report_api_access_query.search_access_groups.return_value = {
        "count": 0,
        "items": [],
    }

    inputs = QueryReportInputs(access_group_name="NonExistent")
    result = report_access_query(
        api=mock_api,
        inputs=inputs,
        output_config=mock_output_config_access_query,
        report_ids=mock_report_ids_access_query,
        requested_fields=None,
    )

    assert result["report_path"] is None
    assert result["error_message"] is None
    assert "No access groups found matching" in result["info_message"]


@pytest.mark.unit
def test_report_access_query_role_filter(
    mock_report_api_access_query: MagicMock,
    mock_env_config_access_query: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    mock_json_debug_dumps: MagicMock,  # noqa
    sample_hosts: list,
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    """Test that role_name filter resolves IDs and searches correctly."""
    mock_api = MagicMock()

    mock_report_api_access_query.search_roles.return_value = {
        "count": 1,
        "items": [{"id": "role-1", "name": "Admin Role"}],
    }
    mock_report_api_access_query.hosts.search_hosts.return_value = _create_search_response(sample_hosts)

    mock_report_api_access_query.get_role_members.return_value = {
        "count": 2,
        "items": [
            {"id": "user1", "full_name": "John Doe"},
            {"id": "user2", "full_name": "Jane Smith"},
        ],
    }

    with patch("reports.access.query.report.write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": "/test/report_out/access-query.csv",
            "error_message": None,
            "info_message": None,
        }

        inputs = QueryReportInputs(role_name="Admin Role")
        result = report_access_query(
            api=mock_api,
            inputs=inputs,
            output_config=mock_output_config_access_query,
            report_ids=mock_report_ids_access_query,
            requested_fields=None,
        )

    assert result["report_path"] is not None
    assert result["error_message"] is None
    mock_report_api_access_query.search_roles.assert_called_once()
    mock_report_api_access_query.hosts.search_hosts.assert_called_once()
    call_args = mock_report_api_access_query.hosts.search_hosts.call_args
    search_payload = call_args[0][1]
    assert "role" in search_payload
    assert search_payload["role"] == ["role-1"]


@pytest.mark.unit
def test_report_access_query_role_not_found(
    mock_report_api_access_query: MagicMock,
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    """Test that non-matching role returns info message."""
    mock_api = MagicMock()

    mock_report_api_access_query.search_roles.return_value = {
        "count": 0,
        "items": [],
    }

    inputs = QueryReportInputs(role_name="NonExistent")
    result = report_access_query(
        api=mock_api,
        inputs=inputs,
        output_config=mock_output_config_access_query,
        report_ids=mock_report_ids_access_query,
        requested_fields=None,
    )

    assert result["report_path"] is None
    assert result["error_message"] is None
    assert "No role found with exact name 'NonExistent'" == result["info_message"]


@pytest.mark.unit
def test_report_access_query_service_type_filter(
    mock_report_api_access_query: MagicMock,
    mock_env_config_access_query: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    mock_json_debug_dumps: MagicMock,  # noqa
    sample_hosts: list,
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    """Test that service_type filter works correctly."""
    mock_api = MagicMock()

    mock_report_api_access_query.hosts.search_hosts.return_value = _create_search_response(sample_hosts)

    mock_report_api_access_query.get_role_members.return_value = {
        "count": 2,
        "items": [
            {"id": "user1", "full_name": "John Doe"},
            {"id": "user2", "full_name": "Jane Smith"},
        ],
    }

    with patch("reports.access.query.report.write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": "/test/report_out/access-query.csv",
            "error_message": None,
            "info_message": None,
        }

        inputs = QueryReportInputs(target_address=sample_hosts[0]["addresses"][0], service_type="SSH")
        result = report_access_query(
            api=mock_api,
            inputs=inputs,
            output_config=mock_output_config_access_query,
            report_ids=mock_report_ids_access_query,
            requested_fields=None,
        )

    assert result["report_path"] is not None
    assert result["error_message"] is None
    mock_report_api_access_query.hosts.search_hosts.assert_called_once()
    call_args = mock_report_api_access_query.hosts.search_hosts.call_args
    search_payload = call_args[0][1]
    assert "service" in search_payload
    assert search_payload["service"] == ["SSH"]


@pytest.mark.unit
def test_report_access_query_user_name_filter(
    mock_report_api_access_query: MagicMock,
    mock_env_config_access_query: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    mock_json_debug_dumps: MagicMock,  # noqa
    sample_hosts: list,
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    """Test that user_name filter post-filters correctly."""
    mock_api = MagicMock()

    mock_report_api_access_query.hosts.search_hosts.return_value = _create_search_response(sample_hosts)

    mock_report_api_access_query.get_role_members.return_value = {
        "count": 2,
        "items": [
            {"id": "user1", "full_name": "John Doe"},
            {"id": "user2", "full_name": "Jane Smith"},
        ],
    }

    with patch("reports.access.query.report.write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": "/test/report_out/access-query.csv",
            "error_message": None,
            "info_message": None,
        }

        inputs = QueryReportInputs(
            target_address=sample_hosts[0]["addresses"][0],
            user_name="Jane",
        )
        result = report_access_query(
            api=mock_api,
            inputs=inputs,
            output_config=mock_output_config_access_query,
            report_ids=mock_report_ids_access_query,
            requested_fields=None,
        )

    assert result["report_path"] is not None
    assert result["error_message"] is None
    mock_write.assert_called_once()
    output_data = mock_write.call_args[0][4]
    for record in output_data:
        assert "Jane" in record.get("user_name", "")


@pytest.mark.unit
def test_report_access_query_user_name_no_match(
    mock_report_api_access_query: MagicMock,
    mock_env_config_access_query: MagicMock,  # noqa
    sample_hosts: list,
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    """Test that user_name filter returns empty when no match."""
    mock_api = MagicMock()

    mock_report_api_access_query.hosts.search_hosts.return_value = _create_search_response(sample_hosts)

    mock_report_api_access_query.get_role_members.return_value = {
        "count": 2,
        "items": [
            {"id": "user1", "full_name": "John Doe"},
            {"id": "user2", "full_name": "Jane Smith"},
        ],
    }

    inputs = QueryReportInputs(
        target_address=sample_hosts[0]["addresses"][0],
        user_name="NonExistentUser",
    )
    result = report_access_query(
        api=mock_api,
        inputs=inputs,
        output_config=mock_output_config_access_query,
        report_ids=mock_report_ids_access_query,
        requested_fields=None,
    )

    assert result["report_path"] is None
    assert result["error_message"] is None
    assert "No access entries found matching the specified filters" in result["info_message"]


@pytest.mark.unit
def test_report_access_query_with_pagination(
    mock_report_api_access_query: MagicMock,
    mock_env_config_access_query: MagicMock,
    mock_path_mkdir: MagicMock,  # noqa
    sample_host: dict,
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    """Test that report_access_query handles paginated API responses."""
    mock_api = MagicMock()
    batch_size = 2

    mock_env_config_access_query.get_api_batchsize.return_value = batch_size

    hosts_page1 = [
        {**sample_host, "id": "host-1", "addresses": ["server1.example.com"], "access_group_id": ""},
        {**sample_host, "id": "host-2", "addresses": ["server2.example.com"], "access_group_id": ""},
    ]
    hosts_page2 = [
        {**sample_host, "id": "host-3", "addresses": ["server3.example.com"], "access_group_id": ""},
    ]

    mock_report_api_access_query.hosts.search_hosts.side_effect = [
        {"count": 3, "items": hosts_page1},
        {"count": 3, "items": hosts_page2},
    ]

    mock_report_api_access_query.get_role_members.return_value = {
        "count": 2,
        "items": [
            {"id": "user1", "full_name": "John Doe"},
            {"id": "user2", "full_name": "Jane Smith"},
        ],
    }

    with patch("reports.access.query.report.write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": "/test/report_out/access-query.csv",
            "error_message": None,
            "info_message": None,
        }

        inputs = QueryReportInputs(target_address="server")
        result = report_access_query(
            api=mock_api,
            inputs=inputs,
            output_config=mock_output_config_access_query,
            report_ids=mock_report_ids_access_query,
            requested_fields=None,
        )

    assert result["report_path"] is not None
    assert result["error_message"] is None
    assert mock_report_api_access_query.hosts.search_hosts.call_count >= 1


@pytest.mark.unit
def test_report_access_query_multiple_filters(
    mock_report_api_access_query: MagicMock,
    mock_env_config_access_query: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    mock_json_debug_dumps: MagicMock,  # noqa
    sample_hosts: list,
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    """Test that multiple filters work together correctly."""
    mock_api = MagicMock()

    mock_report_api_access_query.search_access_groups.return_value = {
        "count": 1,
        "items": [{"id": "ag-1", "name": "Production Access"}],
    }
    mock_report_api_access_query.hosts.search_hosts.return_value = _create_search_response(sample_hosts)

    mock_report_api_access_query.get_role_members.return_value = {
        "count": 2,
        "items": [
            {"id": "user1", "full_name": "John Doe"},
            {"id": "user2", "full_name": "Jane Smith"},
        ],
    }

    with patch("reports.access.query.report.write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": "/test/report_out/access-query.csv",
            "error_message": None,
            "info_message": None,
        }

        inputs = QueryReportInputs(
            target_address=sample_hosts[0]["addresses"][0],
            access_group_name="Production",
            service_type="SSH",
        )
        result = report_access_query(
            api=mock_api,
            inputs=inputs,
            output_config=mock_output_config_access_query,
            report_ids=mock_report_ids_access_query,
            requested_fields=None,
        )

    assert result["report_path"] is not None
    assert result["error_message"] is None
    call_args = mock_report_api_access_query.hosts.search_hosts.call_args
    search_payload = call_args[0][1]
    assert "keywords" in search_payload
    assert "access_group_ids" in search_payload
    assert "service" in search_payload
    assert search_payload["service"] == ["SSH"]


@pytest.mark.unit
def test_report_access_query_missing_fields(
    mock_report_api_access_query: MagicMock,
    mock_env_config_access_query: MagicMock,  # noqa
    mock_path_mkdir: MagicMock,  # noqa
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    """Test that report_access_query handles missing fields with empty strings."""
    mock_api = MagicMock()

    host_with_missing_fields = {
        "id": "host-1",
        "addresses": [],
        "common_name": "",
        "principals": [
            {
                "principal": "root",
                "roles": [{"id": "role-1", "name": "admin-role"}],
            }
        ],
    }

    mock_report_api_access_query.hosts.search_hosts.return_value = _create_search_response([host_with_missing_fields])

    mock_report_api_access_query.get_role_members.return_value = {
        "count": 1,
        "items": [
            {"id": "user1", "full_name": "John Doe"},
        ],
    }

    with patch("reports.access.query.report.write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": "/test/report_out/access-query.csv",
            "error_message": None,
            "info_message": None,
        }

        inputs = QueryReportInputs(target_address="test")
        result = report_access_query(
            api=mock_api,
            inputs=inputs,
            output_config=mock_output_config_access_query,
            report_ids=mock_report_ids_access_query,
            requested_fields=None,
        )

    assert result["report_path"] is not None
    mock_write.assert_called_once()
    output_data = mock_write.call_args[0][4]
    assert len(output_data) >= 1


@pytest.mark.unit
def test_report_access_query_single_tag_filter(
    mock_report_api_access_query: MagicMock,
    mock_env_config_access_query: MagicMock,
    mock_path_mkdir: MagicMock,
    mock_json_debug_dumps: MagicMock,  # noqa
    sample_hosts: list,
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    """Test that single tag filter works correctly."""
    mock_api = MagicMock()

    mock_report_api_access_query.hosts.search_hosts.return_value = _create_search_response(sample_hosts)

    mock_report_api_access_query.get_role_members.return_value = {
        "count": 1,
        "items": [
            {"id": "user1", "full_name": "John Doe"},
        ],
    }

    with patch("reports.access.query.report.write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": "/test/report_out/access-query.csv",
            "error_message": None,
            "info_message": None,
        }

        inputs = QueryReportInputs(tags="production")
        result = report_access_query(
            api=mock_api,
            inputs=inputs,
            output_config=mock_output_config_access_query,
            report_ids=mock_report_ids_access_query,
            requested_fields=None,
        )

    assert result["report_path"] is not None
    assert result["error_message"] is None
    mock_report_api_access_query.hosts.search_hosts.assert_called_once()
    call_args = mock_report_api_access_query.hosts.search_hosts.call_args
    search_payload = call_args[0][1]
    assert "tags" in search_payload
    assert search_payload["tags"] == ["production"]


@pytest.mark.unit
def test_report_access_query_multiple_tags_filter(
    mock_report_api_access_query: MagicMock,
    mock_env_config_access_query: MagicMock,
    mock_path_mkdir: MagicMock,
    mock_json_debug_dumps: MagicMock,  # noqa
    sample_hosts: list,
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    """Test that comma-separated tags filter works correctly."""
    mock_api = MagicMock()

    mock_report_api_access_query.hosts.search_hosts.return_value = _create_search_response(sample_hosts)

    mock_report_api_access_query.get_role_members.return_value = {
        "count": 1,
        "items": [
            {"id": "user1", "full_name": "John Doe"},
        ],
    }

    with patch("reports.access.query.report.write_report_output") as mock_write:
        mock_write.return_value = {
            "report_path": "/test/report_out/access-query.csv",
            "error_message": None,
            "info_message": None,
        }

        inputs = QueryReportInputs(tags="production, linux, aws")
        result = report_access_query(
            api=mock_api,
            inputs=inputs,
            output_config=mock_output_config_access_query,
            report_ids=mock_report_ids_access_query,
            requested_fields=None,
        )

    assert result["report_path"] is not None
    assert result["error_message"] is None
    mock_report_api_access_query.hosts.search_hosts.assert_called_once()
    call_args = mock_report_api_access_query.hosts.search_hosts.call_args
    search_payload = call_args[0][1]
    assert "tags" in search_payload
    assert search_payload["tags"] == ["production", "linux", "aws"]


@pytest.mark.unit
def test_report_access_query_filters_hosts_by_user_group(
    mock_report_api_access_query: MagicMock,
    mock_output_config_access_query: dict,
    mock_report_ids_access_query: dict,
) -> None:
    mock_api = MagicMock()
    mock_report_api_access_query.hosts.search_hosts.return_value = {
        "count": 2,
        "items": [
            {
                "id": "host-allowed",
                "access_group_id": "ag-1",
                "addresses": ["server1.example.com"],
                "common_name": "server1",
                "services": [],
                "principals": [{"principal": "root", "roles": [{"id": "role-1", "name": "role-1"}]}],
            },
            {
                "id": "host-blocked",
                "access_group_id": "ag-2",
                "addresses": ["server2.example.com"],
                "common_name": "server2",
                "services": [],
                "principals": [{"principal": "root", "roles": [{"id": "role-2", "name": "role-2"}]}],
            },
        ],
    }
    mock_report_api_access_query.get_role_members.return_value = {
        "count": 1,
        "items": [{"id": "user1", "full_name": "John Doe"}],
    }

    with (
        patch.object(query_report_module, "resolve_allowed_access_group_ids", return_value=({"ag-1"}, None)),
        patch.object(query_report_module, "write_report_output") as mock_write,
    ):
        mock_write.return_value = {"report_path": "/tmp/access-query.csv", "error_message": None, "info_message": None}
        result = report_access_query(
            api=mock_api,
            inputs=QueryReportInputs(target_address="server"),
            output_config=mock_output_config_access_query,
            report_ids=mock_report_ids_access_query,
            requested_fields=None,
            user_group_id="10",
        )

    assert result["error_message"] is None
    output_rows = mock_write.call_args[0][4]
    assert output_rows
    for row in output_rows:
        assert row["target_host_id"] == "host-allowed"
