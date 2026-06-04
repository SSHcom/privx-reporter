"""Tests for events accounts report."""

from unittest.mock import MagicMock, patch

import pytest

from reports.events._shared.models import EventsAccountsReportInputs
from reports.events.accounts.report import report_account_events_by_date_range


def _account_event_with_added_principal() -> dict:
    return {
        "event_id": "802",
        "event_name": "Host account changed",
        "service_name": "svc",
        "message": {
            "timestamp": "2026-01-01T12:00:00Z",
            "modifications": {
                "Principals.0.Principal": {"old_value": "", "new_value": "root"},
                "Principals.0.Roles.0.Name": {"old_value": "", "new_value": "admin"},
                "Principals.0.Roles.0.ID": {"old_value": "", "new_value": "role-1"},
            },
        },
    }


def _account_event_with_removed_principal() -> dict:
    return {
        "event_id": "802",
        "event_name": "Host account changed",
        "service_name": "svc",
        "message": {
            "timestamp": "2026-01-01T12:00:00Z",
            "modifications": {
                "Principals.0.Principal": {"old_value": "root", "new_value": ""},
                "Principals.0.Roles.0.Name": {"old_value": "admin", "new_value": ""},
                "Principals.0.Roles.0.ID": {"old_value": "role-1", "new_value": ""},
            },
        },
    }


def _account_event_with_modified_principal() -> dict:
    return {
        "event_id": "802",
        "event_name": "Host account changed",
        "service_name": "svc",
        "message": {
            "timestamp": "2026-01-01T12:00:00Z",
            "modifications": {
                "Principals.0.Principal": {"old_value": "old-user", "new_value": "new-user"},
                "Principals.0.Roles.0.Name": {"old_value": "admin", "new_value": "auditor"},
                "Principals.0.Roles.0.ID": {"old_value": "role-old", "new_value": "role-new"},
            },
        },
    }


def _account_event_with_two_added_principals() -> dict:
    return {
        "event_id": "802",
        "event_name": "Host account changed",
        "service_name": "svc",
        "message": {
            "timestamp": "2026-01-01T12:00:00Z",
            "modifications": {
                "Principals.0.Principal": {"old_value": "", "new_value": "root"},
                "Principals.0.Roles.0.Name": {"old_value": "", "new_value": "admin"},
                "Principals.0.Roles.0.ID": {"old_value": "", "new_value": "role-1"},
                "Principals.1.Principal": {"old_value": "", "new_value": "deploy"},
                "Principals.1.Roles.0.Name": {"old_value": "", "new_value": "ops"},
                "Principals.1.Roles.0.ID": {"old_value": "", "new_value": "role-2"},
            },
        },
    }


@pytest.mark.unit
def test_accounts_returns_db_error_on_fetch_failure(
    events_accounts_output_config: dict,
    report_ids_events_accounts: object,
) -> None:
    with patch("reports.events.accounts.report._fetch_events", side_effect=RuntimeError("db down")):
        result = report_account_events_by_date_range(
            _api=MagicMock(),
            inputs=EventsAccountsReportInputs(),
            output_config=events_accounts_output_config,
            report_ids=report_ids_events_accounts,
        )

    assert result == {
        "report_path": None,
        "error_message": "Database error. Make sure the database is running and accessible.",
        "info_message": None,
    }


@pytest.mark.unit
def test_accounts_malformed_modifications_are_ignored(
    events_accounts_output_config: dict,
    report_ids_events_accounts: object,
) -> None:
    bad_event = {
        "event_id": "802",
        "event_name": "Host account changed",
        "message": {"modifications": "{not-json"},
    }
    with patch("reports.events.accounts.report._fetch_events", return_value=[bad_event]):
        result = report_account_events_by_date_range(
            _api=MagicMock(),
            inputs=EventsAccountsReportInputs(),
            output_config=events_accounts_output_config,
            report_ids=report_ids_events_accounts,
        )

    assert result == {
        "report_path": None,
        "error_message": None,
        "info_message": "No account addition or removal events found within the specified date range",
    }


@pytest.mark.unit
def test_accounts_happy_path_writes_output(
    events_accounts_output_config: dict,
    report_ids_events_accounts: object,
) -> None:
    with (
        patch(
            "reports.events.accounts.report._fetch_events",
            return_value=[_account_event_with_added_principal()],
        ),
        patch("reports.events.accounts.report.write_report_output") as mock_write_report_output,
    ):
        mock_write_report_output.return_value = {
            "report_path": "/tmp/events-accounts.csv",
            "error_message": None,
            "info_message": None,
        }
        result = report_account_events_by_date_range(
            _api=MagicMock(),
            inputs=EventsAccountsReportInputs(),
            output_config=events_accounts_output_config,
            report_ids=report_ids_events_accounts,
        )

    assert result["report_path"] == "/tmp/events-accounts.csv"
    rows = mock_write_report_output.call_args[0][4]
    assert rows[0]["action"] == "Added"
    assert rows[0]["principal"] == "root"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("inputs", "event_factory", "expected_action"),
    [
        (EventsAccountsReportInputs(added=True), _account_event_with_added_principal, "Added"),
        (EventsAccountsReportInputs(removed=True), _account_event_with_removed_principal, "Removed"),
    ],
)
def test_accounts_action_filters(
    events_accounts_output_config: dict,
    report_ids_events_accounts: object,
    inputs: EventsAccountsReportInputs,
    event_factory: object,
    expected_action: str,
) -> None:
    with (
        patch("reports.events.accounts.report._fetch_events", return_value=[event_factory()]),
        patch("reports.events.accounts.report.write_report_output") as mock_write_report_output,
    ):
        mock_write_report_output.return_value = {
            "report_path": "/tmp/events-accounts.csv",
            "error_message": None,
            "info_message": None,
        }
        result = report_account_events_by_date_range(
            _api=MagicMock(),
            inputs=inputs,
            output_config=events_accounts_output_config,
            report_ids=report_ids_events_accounts,
        )

    assert result["error_message"] is None
    rows = mock_write_report_output.call_args[0][4]
    assert len(rows) == 1
    assert rows[0]["action"] == expected_action


@pytest.mark.unit
def test_accounts_extracts_removed_and_modified_actions(
    events_accounts_output_config: dict,
    report_ids_events_accounts: object,
) -> None:
    with (
        patch(
            "reports.events.accounts.report._fetch_events",
            return_value=[_account_event_with_removed_principal(), _account_event_with_modified_principal()],
        ),
        patch("reports.events.accounts.report.write_report_output") as mock_write_report_output,
    ):
        mock_write_report_output.return_value = {
            "report_path": "/tmp/events-accounts.csv",
            "error_message": None,
            "info_message": None,
        }
        result = report_account_events_by_date_range(
            _api=MagicMock(),
            inputs=EventsAccountsReportInputs(),
            output_config=events_accounts_output_config,
            report_ids=report_ids_events_accounts,
        )

    assert result["error_message"] is None
    rows = mock_write_report_output.call_args[0][4]
    assert [row["action"] for row in rows] == ["Removed", "Modified"]


@pytest.mark.unit
def test_accounts_extracts_multiple_principals(
    events_accounts_output_config: dict,
    report_ids_events_accounts: object,
) -> None:
    with (
        patch(
            "reports.events.accounts.report._fetch_events",
            return_value=[_account_event_with_two_added_principals()]
        ),
        patch("reports.events.accounts.report.write_report_output") as mock_write_report_output,
    ):
        mock_write_report_output.return_value = {
            "report_path": "/tmp/events-accounts.csv",
            "error_message": None,
            "info_message": None,
        }
        report_account_events_by_date_range(
            _api=MagicMock(),
            inputs=EventsAccountsReportInputs(),
            output_config=events_accounts_output_config,
            report_ids=report_ids_events_accounts,
        )

    rows = mock_write_report_output.call_args[0][4]
    assert len(rows) == 2
    assert {row["principal"] for row in rows} == {"root", "deploy"}
