"""Tests for events role-members report."""

from unittest.mock import MagicMock, patch

import pytest

from reports.events._shared.models import EventsRoleMembersReportInputs
from reports.events.role_members.report import report_role_member_events_by_date_range


def _role_member_change_event() -> dict:
    return {
        "event_id": "220",
        "event_name": "Role members changed",
        "service_name": "svc",
        "message": {
            "targetUserID": "user-1",
            "principal": "alice",
            "modifications": {
                "Roles": {
                    "old_value": [{"id": "role-1", "name": "Old", "grant_type": "manual"}],
                    "new_value": [{"id": "role-2", "name": "New", "grant_type": "manual"}],
                }
            },
        },
    }


@pytest.mark.unit
def test_role_members_returns_db_error_on_fetch_failure(
    events_role_members_output_config: dict,
    report_ids_events_role_members: object,
) -> None:
    with patch("reports.events.role_members.report._fetch_events", side_effect=RuntimeError("db down")):
        result = report_role_member_events_by_date_range(
            _api=MagicMock(),
            inputs=EventsRoleMembersReportInputs(),
            output_config=events_role_members_output_config,
            report_ids=report_ids_events_role_members,
        )

    assert result == {
        "report_path": None,
        "error_message": "Database error. Make sure the database is running and accessible.",
        "info_message": None,
    }


@pytest.mark.unit
def test_role_members_returns_info_for_no_events(
    events_role_members_output_config: dict,
    report_ids_events_role_members: object,
) -> None:
    with patch("reports.events.role_members.report._fetch_events", return_value=[]):
        result = report_role_member_events_by_date_range(
            _api=MagicMock(),
            inputs=EventsRoleMembersReportInputs(),
            output_config=events_role_members_output_config,
            report_ids=report_ids_events_role_members,
        )

    assert result == {
        "report_path": None,
        "error_message": None,
        "info_message": "No role member addition or removal events found within the specified date range",
    }


@pytest.mark.unit
def test_role_members_added_filter_keeps_only_additions(
    events_role_members_output_config: dict,
    report_ids_events_role_members: object,
) -> None:
    with (
        patch("reports.events.role_members.report._fetch_events", return_value=[_role_member_change_event()]),
        patch("reports.events.role_members.report.write_report_output") as mock_write_report_output,
    ):
        mock_write_report_output.return_value = {
            "report_path": "/tmp/events-role-members.csv",
            "error_message": None,
            "info_message": None,
        }
        result = report_role_member_events_by_date_range(
            _api=MagicMock(),
            inputs=EventsRoleMembersReportInputs(added=True),
            output_config=events_role_members_output_config,
            report_ids=report_ids_events_role_members,
        )

    assert result["report_path"] == "/tmp/events-role-members.csv"
    rows = mock_write_report_output.call_args[0][4]
    assert len(rows) == 1
    assert rows[0]["action"] == "add"
    assert rows[0]["role_id"] == "role-2"
