"""Tests for list sources report."""

from unittest.mock import MagicMock, patch

import pytest

from reports._shared.input import BaseReportInputs
from reports.list.sources.report import list_sources
from tests.reports.list.helpers import output_config, report_ids


@pytest.mark.unit
def test_list_sources_success_empty_and_api_failure() -> None:
    config = output_config("sources", {"id": "true|ID", "name": "true|Name"})
    mock_api = MagicMock()
    mock_api.get_sources.return_value = MagicMock(ok=True, data={"items": [{"id": "src-1", "name": "LDAP"}]})
    with patch("reports.list.sources.report.write_report_output") as mock_write:
        mock_write.return_value = {"report_path": "/tmp/sources.csv", "error_message": None, "info_message": None}
        result = list_sources(mock_api, config, report_ids("sources"), BaseReportInputs())
    assert result["report_path"] == "/tmp/sources.csv"

    empty_api = MagicMock()
    empty_api.get_sources.return_value = MagicMock(ok=True, data={"items": []})
    empty_result = list_sources(empty_api, config, report_ids("sources"), BaseReportInputs())
    assert empty_result["info_message"] == "No sources found"

    fail_api = MagicMock()
    fail_api.get_sources.return_value = MagicMock(ok=False, data={})
    fail_result = list_sources(fail_api, config, report_ids("sources"), BaseReportInputs())
    assert "Failed to retrieve sources from PrivX API" in fail_result["error_message"]
