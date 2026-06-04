"""Tests for roles user report functions."""

from unittest.mock import MagicMock

import pytest

from reports.roles._shared.models import UserReportInputs
from reports.roles.user import report as roles_user_module


@pytest.mark.unit
def test_report_user_roles_success(
    mock_report_api_user: MagicMock,
    mock_env_config_user: MagicMock,  # noqa
    mock_csv_writer_user: MagicMock,  # noqa
    mock_report_ids_user: dict,
    mock_output_config_user: dict,
    standard_csv_dir: str,
) -> None:
    """Test user roles are correctly retrieved and written to CSV."""
    from tests.fixtures.data_factories import create_role

    mock_api = MagicMock()
    user_name = "testuser"

    mock_report_api_user.users.search_users.return_value = {"items": [{"id": "user-123", "principal": user_name}]}
    mock_user_roles = [
        create_role("role1", "admin"),
        create_role("role2", "user"),
    ]
    mock_report_api_user.get_user_roles.return_value = mock_user_roles
    mock_report_api_user.get_access_group_by_id.return_value = {
        "name": "test-group",
        "comment": "Test Group",
        "default": False,
    }

    result = roles_user_module.report_user_roles(
        mock_api, UserReportInputs(user_name=user_name), mock_output_config_user, mock_report_ids_user
    )

    mock_report_api_user.users.search_users.assert_called_once_with(mock_api, search_payload={"keywords": user_name})
    assert result["report_path"] == standard_csv_dir
    assert result["error_message"] is None


@pytest.mark.unit
def test_report_user_roles_no_user_found(
    mock_report_api_user: MagicMock,
    mock_report_ids_user: dict,
    mock_output_config_user: dict,
) -> None:
    """Test report_user_roles when user is not found."""
    mock_api = MagicMock()
    user_name = "nonexistent"

    mock_report_api_user.users.search_users.return_value = {"items": []}

    result = roles_user_module.report_user_roles(
        mock_api, UserReportInputs(user_name=user_name), mock_output_config_user, mock_report_ids_user
    )

    mock_report_api_user.users.search_users.assert_called_once_with(mock_api, search_payload={"keywords": user_name})
    mock_report_api_user.get_user_roles.assert_not_called()
    assert result["report_path"] is None
    assert result["error_message"] is None
    assert result["info_message"] == f"No users found matching '{user_name}'"


@pytest.mark.unit
def test_report_user_roles_no_roles_found(
    mock_report_api_user: MagicMock,
    mock_env_config_user: MagicMock,  # noqa
    mock_csv_writer_user: MagicMock,  # noqa
    mock_report_ids_user: dict,
    mock_output_config_user: dict,
) -> None:
    """Test report_user_roles when no roles are found for a user."""
    mock_api = MagicMock()
    user_name = "testuser"

    mock_report_api_user.users.search_users.return_value = {"items": [{"id": "user-123", "principal": user_name}]}
    mock_report_api_user.get_user_roles.return_value = []

    result = roles_user_module.report_user_roles(
        mock_api, UserReportInputs(user_name=user_name), mock_output_config_user, mock_report_ids_user
    )

    mock_report_api_user.users.search_users.assert_called_once_with(mock_api, search_payload={"keywords": user_name})
    mock_report_api_user.get_user_roles.assert_called_once()
    assert result["report_path"] is None
    assert result["error_message"] is None
    assert result["info_message"] == f"No roles found for any user matching '{user_name}'"
