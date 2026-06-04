"""Tests for list roles report."""

from unittest.mock import MagicMock, patch

import pytest

from reports._shared.input import BaseReportInputs
from reports.list.roles.report import list_roles
from tests.reports.list.helpers import output_config, report_ids


@pytest.mark.unit
def test_list_roles_success_and_output_config_failure() -> None:
    config = output_config("roles", {"id": "true|ID", "name": "true|Name"})
    with (
        patch("reports.list.roles.report.report_api") as mock_report_api,
        patch("reports.list.roles.report.write_report_output") as mock_write,
    ):
        mock_report_api.roles.get_all_roles.return_value = [{"id": "role-1", "name": "Admin"}]
        mock_report_api.access_group.search_access_groups.return_value = {"items": []}
        mock_write.return_value = {"report_path": "/tmp/roles.csv", "error_message": None, "info_message": None}
        result = list_roles(MagicMock(), config, report_ids("roles"), BaseReportInputs())
    assert result["report_path"] == "/tmp/roles.csv"

    with patch("reports.list.roles.report.report_api") as mock_report_api:
        mock_report_api.roles.get_all_roles.return_value = [{"id": "role-1", "name": "Admin"}]
        fail_result = list_roles(MagicMock(), {}, report_ids("roles"), BaseReportInputs())
    assert "Output configuration is required" in fail_result["error_message"]
