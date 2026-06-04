"""Tests for list hosts report."""

from unittest.mock import MagicMock, patch

import pytest

from reports._shared.input import BaseReportInputs
from reports.list.hosts.report import list_hosts
from tests.reports.list.helpers import output_config, report_ids


@pytest.mark.unit
def test_list_hosts_success_and_empty_paths() -> None:
    config = output_config("hosts", {"id": "true|ID", "common_name": "true|Host"})
    with (
        patch("reports.list.hosts.report.report_api") as mock_report_api,
        patch("reports.list.hosts.report.write_report_output") as mock_write,
    ):
        mock_report_api.hosts.get_all_hosts.return_value = [{"id": "host-1", "common_name": "host1"}]
        mock_report_api.access_group.search_access_groups.return_value = {"items": []}
        mock_write.return_value = {"report_path": "/tmp/hosts.csv", "error_message": None, "info_message": None}
        result = list_hosts(MagicMock(), config, report_ids("hosts"), BaseReportInputs())
    assert result["report_path"] == "/tmp/hosts.csv"

    with patch("reports.list.hosts.report.report_api") as mock_report_api:
        mock_report_api.hosts.get_all_hosts.return_value = []
        empty_result = list_hosts(MagicMock(), config, report_ids("hosts"), BaseReportInputs())
    assert empty_result["info_message"] == "No hosts found"


@pytest.mark.unit
def test_list_hosts_filters_by_user_group() -> None:
    config = output_config("hosts", {"id": "true|ID", "common_name": "true|Host"})
    with (
        patch("reports.list.hosts.report.report_api") as mock_report_api,
        patch("reports.list.hosts.report.resolve_allowed_access_group_ids") as mock_resolve,
        patch("reports.list.hosts.report.write_report_output") as mock_write,
    ):
        mock_resolve.return_value = ({"ag-1"}, None)
        mock_report_api.hosts.get_all_hosts.return_value = [
            {"id": "host-1", "common_name": "host1", "access_group_id": "ag-1"},
            {"id": "host-2", "common_name": "host2", "access_group_id": "ag-2"},
        ]
        mock_report_api.access_group.search_access_groups.return_value = {"items": []}
        mock_write.return_value = {"report_path": "/tmp/hosts.csv", "error_message": None, "info_message": None}

        result = list_hosts(
            MagicMock(),
            config,
            report_ids("hosts"),
            BaseReportInputs(),
            user_group_id="10",
        )

    assert result["error_message"] is None
    ordered_output = mock_write.call_args[0][4]
    assert len(ordered_output) == 1
    assert ordered_output[0]["id"] == "host-1"
