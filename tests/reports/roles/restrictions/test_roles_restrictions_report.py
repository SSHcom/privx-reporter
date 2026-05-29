"""Tests for roles restrictions report functions."""

from unittest.mock import MagicMock

import pytest

from lib.utils.config.report_ids import ReportIds
from reports.roles._shared.models import RestrictionsReportInputs
from reports.roles.restrictions import report as roles_restrictions_module


@pytest.mark.unit
def test_report_context_restrict_success(
    mock_report_api_context_restrict: MagicMock,
    mock_env_config_context_restrict: MagicMock,  # noqa
    mock_csv_writer_context_restrict: MagicMock,  # noqa
    mock_output_config_context_restrict: dict,
    standard_csv_dir: str,
) -> None:
    """Test report_role_restrictions when roles with context restrictions are found."""
    from tests.fixtures.data_factories import create_role

    mock_api = MagicMock()
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
        create_role("role2", "unrestricted-role", context={"enabled": False}),
        create_role("role3", "no-context-role"),
    ]
    mock_report_api_context_restrict.get_roles.return_value = mock_roles

    result = roles_restrictions_module.report_role_restrictions(
        mock_api,
        RestrictionsReportInputs(),
        mock_output_config_context_restrict,
        ReportIds(
            command="roles",
            sub_command="restrictions",
            report_prefix="roles-restrictions",
            config_key="roles.subcommands.restrictions",
        ),
    )

    assert result["report_path"] == standard_csv_dir
    assert result["error_message"] is None
    assert result["info_message"] is None


@pytest.mark.unit
def test_report_context_restrict_missing_context_fields(
    mock_report_api_context_restrict: MagicMock,
    mock_env_config_context_restrict: MagicMock,  # noqa
    mock_csv_writer_context_restrict: MagicMock,  # noqa
    mock_output_config_context_restrict: dict,
    standard_csv_dir: str,
) -> None:
    """Test report_role_restrictions when context has missing optional fields."""
    from tests.fixtures.data_factories import create_role

    mock_api = MagicMock()
    mock_roles = [
        create_role(
            "role1",
            "minimal-context-role",
            context={
                "enabled": True,
                # Missing most fields
            },
        ),
    ]
    mock_report_api_context_restrict.get_roles.return_value = mock_roles

    result = roles_restrictions_module.report_role_restrictions(
        mock_api,
        RestrictionsReportInputs(),
        mock_output_config_context_restrict,
        ReportIds(
            command="roles",
            sub_command="restrictions",
            report_prefix="roles-restrictions",
            config_key="roles.subcommands.restrictions",
        ),
    )

    assert result["report_path"] == standard_csv_dir
    assert result["error_message"] is None
