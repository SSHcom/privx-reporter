"""Tests for list network targets report."""

from unittest.mock import MagicMock, patch

import pytest

from reports._shared.input import BaseReportInputs
from reports.list.network_targets.report import list_network_targets
from tests.reports.list.helpers import output_config, report_ids


@pytest.mark.unit
def test_list_network_targets_success_and_empty_paths() -> None:
    config = output_config("network-targets", {"id": "true|ID", "name": "true|Name", "dst": "true|Destination"})
    with (
        patch("reports.list.network_targets.report.report_api") as mock_report_api,
        patch("reports.list.network_targets.report.write_report_output") as mock_write,
    ):
        mock_report_api.network_targets.get_all_network_targets.return_value = [
            {
                "id": "nt-1",
                "name": "net",
                "dst": [{"selector": {"ip": {"start": "1.1.1.1", "end": "1.1.1.1"}}}],
            }
        ]
        mock_write.return_value = {
            "report_path": "/tmp/network-targets.csv",
            "error_message": None,
            "info_message": None,
        }
        result = list_network_targets(MagicMock(), config, report_ids("network-targets"), BaseReportInputs())
    assert result["report_path"] == "/tmp/network-targets.csv"

    with patch("reports.list.network_targets.report.report_api") as mock_report_api:
        mock_report_api.network_targets.get_all_network_targets.return_value = []
        empty_result = list_network_targets(MagicMock(), config, report_ids("network-targets"), BaseReportInputs())
    assert empty_result["info_message"] == "No network targets found"
