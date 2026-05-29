"""Tests for roles list report functions."""

from unittest.mock import MagicMock

import pytest

from reports.roles._shared.models import QueryReportInputs
from reports.roles.query import report as roles_query_module


@pytest.mark.unit
def test_report_all_roles_success(
    mock_report_api: MagicMock,
    mock_env_config: MagicMock,
    mock_csv_writer: MagicMock,
    mock_report_ids: dict,
    mock_output_config_all: dict,
    standard_csv_dir: str,
) -> None:
    """Test all roles are correctly retrieved, formatted and written to CSV."""
    from tests.fixtures.data_factories import create_role

    mock_roles = [
        create_role("role1", "admin"),
        create_role("role2", "user"),
    ]
    mock_report_api.roles.get_all_roles.return_value = mock_roles
    mock_report_api.access_group.search_access_groups.return_value = {
        "count": 1,
        "items": [{"id": "ag-1", "name": "test-group"}],
    }

    inputs = QueryReportInputs()
    result = roles_query_module.roles_query(MagicMock(), mock_output_config_all, mock_report_ids, inputs)

    mock_report_api.roles.get_all_roles.assert_called_once()
    assert result["report_path"] == standard_csv_dir
    assert result["error_message"] is None


@pytest.mark.unit
def test_report_all_roles_with_restrictions(
    mock_report_api: MagicMock,
    mock_env_config: MagicMock,
    mock_csv_writer: MagicMock,
    mock_report_ids: dict,
    mock_output_config_all: dict,
    standard_csv_dir: str,
) -> None:
    """Test all roles report includes restriction fields for roles with context."""
    from tests.fixtures.data_factories import create_role

    mock_roles = [
        create_role(
            "role1",
            "restricted-role",
            context={
                "enabled": True,
                "block_role": True,
                "validity": ["MON", "TUE", "WED"],
                "start_time": "09:00",
                "end_time": "17:00",
                "timezone": "Europe/Helsinki",
                "ip_masks": ["192.168.1.0/24", "10.0.0.0/8"],
            },
        ),
        create_role("role2", "unrestricted-role"),
    ]
    mock_report_api.roles.get_all_roles.return_value = mock_roles
    mock_report_api.access_group.search_access_groups.return_value = {
        "count": 1,
        "items": [{"id": "ag-1", "name": "test-group"}],
    }

    inputs = QueryReportInputs()
    result = roles_query_module.roles_query(_mock_api := MagicMock(), mock_output_config_all, mock_report_ids, inputs)

    assert result["report_path"] == standard_csv_dir
    assert result["error_message"] is None


@pytest.mark.unit
def test_report_all_roles_no_roles_found(
    mock_report_api: MagicMock,
    mock_report_ids: dict,
    mock_output_config_all: dict,
) -> None:
    """Test report_all_roles when no roles are found."""
    mock_report_api.roles.get_all_roles.return_value = []

    inputs = QueryReportInputs()
    result = roles_query_module.roles_query(_mock_api := MagicMock(), mock_output_config_all, mock_report_ids, inputs)

    assert result["report_path"] is None
    assert result["error_message"] is None
    assert result["info_message"] == "No roles found"


@pytest.mark.unit
def test_report_roles_with_large_result_set(
    mock_report_api: MagicMock,
    mock_env_config: MagicMock,
    mock_csv_writer: MagicMock,
    mock_report_ids: dict,
    mock_output_config_all: dict,
    standard_csv_dir: str,
) -> None:
    """Test that a large role set is handled correctly."""
    from tests.fixtures.data_factories import create_role

    mock_roles = [create_role(f"role{i}", f"name{i}") for i in range(150)]
    mock_report_api.roles.get_all_roles.return_value = mock_roles
    mock_report_api.access_group.search_access_groups.return_value = {
        "count": 1,
        "items": [{"id": "ag-1", "name": "test-group"}],
    }

    inputs = QueryReportInputs()
    result = roles_query_module.roles_query(MagicMock(), mock_output_config_all, mock_report_ids, inputs)

    mock_report_api.roles.get_all_roles.assert_called_once()
    assert result["report_path"] == standard_csv_dir
    assert result["error_message"] is None
