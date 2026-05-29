"""Tests for events query report."""

from unittest.mock import MagicMock, patch

import pytest

from reports.events._shared.models import EventsQueryReportInputs
from reports.events.query.report import report_events_by_date_range


@pytest.mark.unit
def test_query_requires_a_filter(
    events_query_output_config: dict,
    report_ids_events_query: object,
) -> None:
    result = report_events_by_date_range(
        _api=MagicMock(),
        inputs=EventsQueryReportInputs(),
        output_config=events_query_output_config,
        report_ids=report_ids_events_query,
    )
    assert result["report_path"] is None
    assert "must be provided as a filter" in result["error_message"]
    assert result["info_message"] is None


@pytest.mark.unit
def test_query_returns_db_error_on_fetch_failure(
    events_query_output_config: dict,
    report_ids_events_query: object,
) -> None:
    with patch("reports.events.query.report._fetch_events", side_effect=RuntimeError("db down")):
        result = report_events_by_date_range(
            _api=MagicMock(),
            inputs=EventsQueryReportInputs(event_id="220"),
            output_config=events_query_output_config,
            report_ids=report_ids_events_query,
        )
    assert result == {
        "report_path": None,
        "error_message": "Database error. Make sure the database is running and accessible.",
        "info_message": None,
    }


@pytest.mark.unit
def test_query_returns_info_when_no_events(
    events_query_output_config: dict,
    report_ids_events_query: object,
) -> None:
    with patch("reports.events.query.report._fetch_events", return_value=[]):
        result = report_events_by_date_range(
            _api=MagicMock(),
            inputs=EventsQueryReportInputs(event_name="role"),
            output_config=events_query_output_config,
            report_ids=report_ids_events_query,
        )
    assert result == {
        "report_path": None,
        "error_message": None,
        "info_message": "No events found matching the specified filters",
    }


@pytest.mark.unit
def test_query_happy_path_writes_output(
    events_query_output_config: dict,
    report_ids_events_query: object,
) -> None:
    events = [
        {
            "event_id": "220",
            "event_name": "Role member changed",
            "service_name": "auth",
            "message": {
                "timestamp": "2026-01-01T12:00:00Z",
            },
        }
    ]
    with (
        patch("reports.events.query.report._fetch_events", return_value=events),
        patch("reports.events.query.report.write_report_output") as mock_write_report_output,
    ):
        mock_write_report_output.return_value = {
            "report_path": "/tmp/events-query.csv",
            "error_message": None,
            "info_message": None,
        }
        result = report_events_by_date_range(
            _api=MagicMock(),
            inputs=EventsQueryReportInputs(event_id="220"),
            output_config=events_query_output_config,
            report_ids=report_ids_events_query,
        )

    assert result["report_path"] == "/tmp/events-query.csv"
    assert result["error_message"] is None
    output_rows = mock_write_report_output.call_args[0][4]
    assert output_rows[0]["event_id"] == "220"
