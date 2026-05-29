"""Tests for list events report."""

from unittest.mock import MagicMock, patch

import pytest

from reports._shared.input import BaseReportInputs
from reports.list.events.report import list_events
from tests.reports.list.helpers import output_config, report_ids


@pytest.mark.unit
def test_list_events_success_empty_and_db_failure_paths() -> None:
    config = output_config("events", {"event_id": "true|Event ID", "event_name": "true|Event Name"})
    with (
        patch(
            "reports.list.events.report._fetch_unique_events",
            return_value=[{"event_id": "220", "event_name": "Role"}],
        ),
        patch("reports.list.events.report.write_report_output") as mock_write,
    ):
        mock_write.return_value = {"report_path": "/tmp/events.csv", "error_message": None, "info_message": None}
        result = list_events(MagicMock(), config, report_ids("events"), BaseReportInputs())
    assert result["report_path"] == "/tmp/events.csv"

    with patch("reports.list.events.report._fetch_unique_events", return_value=[]):
        empty_result = list_events(MagicMock(), config, report_ids("events"), BaseReportInputs())
    assert empty_result["info_message"] == "No events found in database"

    with patch("reports.list.events.report._fetch_unique_events", side_effect=RuntimeError("db down")):
        fail_result = list_events(MagicMock(), config, report_ids("events"), BaseReportInputs())
    assert fail_result["error_message"] == "Database error. Make sure the database is running and accessible."
