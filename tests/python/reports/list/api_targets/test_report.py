"""Tests for list api targets report."""

from unittest.mock import MagicMock, patch

import pytest

from reports._shared.input import BaseReportInputs
from reports.list.api_targets.report import list_api_targets
from tests.reports.list.helpers import output_config, report_ids


@pytest.mark.unit
def test_list_api_targets_success_and_output_config_failure() -> None:
    config = output_config("api-targets", {"id": "true|ID", "name": "true|Name"})
    with (
        patch("reports.list.api_targets.report.report_api") as mock_report_api,
        patch("reports.list.api_targets.report.write_report_output") as mock_write,
    ):
        mock_report_api.api_targets.get_all_api_targets.return_value = [
            {"id": "api-1", "name": "api", "access_group_id": "ag-1", "authorized_endpoints": [{"host": "a"}]}
        ]
        mock_report_api.access_group.search_access_groups.return_value = {"items": [{"id": "ag-1", "name": "Ops"}]}
        mock_write.return_value = {"report_path": "/tmp/api-targets.csv", "error_message": None, "info_message": None}
        result = list_api_targets(MagicMock(), config, report_ids("api-targets"), BaseReportInputs())
    assert result["report_path"] == "/tmp/api-targets.csv"

    with patch("reports.list.api_targets.report.report_api") as mock_report_api:
        mock_report_api.api_targets.get_all_api_targets.return_value = [{"id": "api-1", "name": "api"}]
        fail_result = list_api_targets(MagicMock(), {}, report_ids("api-targets"), BaseReportInputs())
    assert "Output configuration is required" in fail_result["error_message"]
