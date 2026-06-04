"""Tests for list access groups report."""

from unittest.mock import MagicMock, patch

import pytest

from reports._shared.input import BaseReportInputs
from reports.list.access_groups.report import list_access_groups
from tests.reports.list.helpers import output_config, report_ids


@pytest.mark.unit
def test_list_access_groups_success_and_empty_paths() -> None:
    config = output_config("access-groups", {"id": "true|ID", "name": "true|Name"})
    with (
        patch("reports.list.access_groups.report.report_api") as mock_report_api,
        patch("reports.list.access_groups.report.write_report_output") as mock_write,
    ):
        mock_report_api.access_group.search_access_groups.return_value = {
            "items": [{"id": "ag-1", "name": "Ops", "comment": "", "default": True}]
        }
        mock_write.return_value = {"report_path": "/tmp/access-groups.csv", "error_message": None, "info_message": None}
        result = list_access_groups(MagicMock(), config, report_ids("access-groups"), BaseReportInputs())

    assert result["report_path"] == "/tmp/access-groups.csv"
    assert mock_write.call_args[0][4][0]["name"] == "Ops"

    with patch("reports.list.access_groups.report.report_api") as mock_report_api:
        mock_report_api.access_group.search_access_groups.return_value = {"items": []}
        empty_result = list_access_groups(MagicMock(), config, report_ids("access-groups"), BaseReportInputs())
    assert empty_result["info_message"] == "No access groups found"
