"""Tests for roles members report functions."""

from unittest.mock import MagicMock, patch

import pytest

from reports.roles._shared.models import MembersReportInputs
from reports.roles.members import report as roles_members_module


@pytest.mark.unit
def test_report_role_members_success(
    mock_report_api_members: MagicMock,
    mock_env_config_members: MagicMock,  # noqa
    mock_csv_writer_members: MagicMock,  # noqa
    mock_report_ids_members: dict,
    mock_output_config_members: dict,
    standard_csv_dir: str,
) -> None:
    """Test role members are correctly retrieved and written to CSV."""
    from tests.fixtures.data_factories import create_role, create_role_member

    mock_api = MagicMock()
    role_name = "admin-role"
    mock_roles = [create_role("role1", role_name)]
    mock_report_api_members.get_roles.return_value = mock_roles
    mock_report_api_members.get_role_members.return_value = {
        "count": 2,
        "items": [
            create_role_member("user1", "User One"),
            create_role_member("user2", "User Two", source_type="LOCAL"),
        ],
    }

    result = roles_members_module.report_role_members(
        mock_api := MagicMock(),
        MembersReportInputs(role_name=role_name),
        mock_output_config_members,
        mock_report_ids_members,
    )

    mock_report_api_members.get_roles.assert_called_once_with(mock_api)
    mock_report_api_members.get_role_members.assert_called_once()
    assert result["report_path"] == standard_csv_dir
    assert result["error_message"] is None


@pytest.mark.unit
def test_report_role_members_with_pagination(
    mock_report_api_members: MagicMock,
    mock_csv_writer_members: MagicMock,  # noqa
    mock_report_ids_members: dict,
    mock_output_config_members: dict,
    standard_csv_dir: str,
) -> None:
    """Test report_role_members with pagination (multiple batches)."""
    from tests.fixtures.data_factories import create_role, create_role_member

    role_name = "admin-role"
    mock_roles = [create_role("role1", role_name)]
    mock_report_api_members.get_roles.return_value = mock_roles
    batch_size = 2
    mock_report_api_members.get_role_members.side_effect = [
        {
            "count": 3,
            "items": [
                create_role_member("user1", "User One"),
                create_role_member("user2", "User Two", source_type="LOCAL"),
            ],
        },
        {
            "count": 3,
            "items": [
                create_role_member("user3", "User Three"),
            ],
        },
    ]

    with patch.object(roles_members_module, "EnvConfig") as mock_env_config:
        mock_env_config.get_api_batchsize.return_value = batch_size
        mock_env_config.get_report_out_dir.return_value = standard_csv_dir

    result = roles_members_module.report_role_members(
        MagicMock(),
        MembersReportInputs(role_name=role_name),
        mock_output_config_members,
        mock_report_ids_members,
    )

    assert mock_report_api_members.get_role_members.call_count == 2
    assert result["report_path"] == standard_csv_dir
    assert result["error_message"] is None


@pytest.mark.unit
def test_report_role_members_role_not_found(
    mock_report_api_members: MagicMock,
    mock_report_ids_members: dict,
    mock_output_config_members: dict,
) -> None:
    """Test report_role_members when role is not found."""
    from tests.fixtures.data_factories import create_role

    mock_api = MagicMock()
    role_name = "nonexistent-role"
    mock_report_api_members.get_roles.return_value = [create_role("role1", "other-role")]

    result = roles_members_module.report_role_members(
        mock_api := MagicMock(),
        MembersReportInputs(role_name=role_name),
        mock_output_config_members,
        mock_report_ids_members,
    )

    mock_report_api_members.get_roles.assert_called_once_with(mock_api)
    mock_report_api_members.get_role_members.assert_not_called()
    assert result["report_path"] is None
    assert result["error_message"] is None


@pytest.mark.unit
@pytest.mark.parametrize("invalid_name", ["", "   ", "\t", "\n"])
def test_report_role_members_invalid_role_name(
    invalid_name: str,
    mock_report_api_members: MagicMock,
    mock_report_ids_members: dict,
    mock_output_config_members: dict,
) -> None:
    """Test report_role_members rejects invalid role names (empty or whitespace)."""
    result = roles_members_module.report_role_members(
        _mock_api := MagicMock(),
        MembersReportInputs(role_name=invalid_name),
        mock_output_config_members,
        mock_report_ids_members,
    )

    mock_report_api_members.get_roles.assert_not_called()
    mock_report_api_members.get_role_members.assert_not_called()
    assert result["report_path"] is None
    assert result["error_message"] is not None
    assert "cannot be empty" in result["error_message"].lower()


@pytest.mark.unit
def test_report_role_members_no_members_found(
    mock_report_api_members: MagicMock,
    mock_env_config_members: MagicMock,  # noqa
    mock_csv_writer_members: MagicMock,  # noqa
    mock_report_ids_members: dict,
    mock_output_config_members: dict,
    standard_csv_dir: str,  # noqa
) -> None:
    """Test report_role_members when role is found but has no members."""
    from tests.fixtures.data_factories import create_role

    mock_api = MagicMock()
    role_name = "admin-role"
    mock_roles = [create_role("role1", role_name)]
    mock_report_api_members.get_roles.return_value = mock_roles
    mock_report_api_members.get_role_members.return_value = {"count": 0, "items": []}

    result = roles_members_module.report_role_members(
        mock_api,
        MembersReportInputs(role_name=role_name),
        mock_output_config_members,
        mock_report_ids_members,
    )

    mock_report_api_members.get_roles.assert_called_once_with(mock_api)
    mock_report_api_members.get_role_members.assert_called_once()
    assert result["report_path"] is None
    assert result["error_message"] is None


@pytest.mark.unit
def test_report_role_members_error_thrown(
    mock_report_api_members: MagicMock,
    mock_env_config_members: MagicMock,  # noqa
    mock_csv_writer_members: MagicMock,  # noqa
    mock_report_ids_members: dict,
    mock_output_config_members: dict,
) -> None:
    """Test report_role_members when get_role_members raises an exception."""
    from tests.fixtures.data_factories import create_role

    mock_api = MagicMock()
    role_name = "admin-role"
    mock_roles = [create_role("role1", role_name)]
    mock_report_api_members.get_roles.return_value = mock_roles
    mock_report_api_members.get_role_members.side_effect = Exception("API error")

    with pytest.raises(Exception, match="API error"):
        roles_members_module.report_role_members(
            mock_api,
            MembersReportInputs(role_name=role_name),
            mock_output_config_members,
            mock_report_ids_members,
        )

    mock_report_api_members.get_roles.assert_called_once_with(mock_api)
    mock_report_api_members.get_role_members.assert_called_once()
