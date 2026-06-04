from unittest.mock import MagicMock, patch

import pytest

from reports.events._shared.helpers import extract_event_fields, resolve_date_range
from reports.events._shared.models import EventsAccountsReportInputs


@pytest.mark.unit
@pytest.mark.parametrize(
    ("inputs", "expected_dates", "expected_days_call"),
    [
        (EventsAccountsReportInputs(days=14), ("2026-01-01", "2026-01-15"), 14),
        (
            EventsAccountsReportInputs(from_date="2026-02-01", to_date="2026-02-28"),
            ("2026-02-01", "2026-02-28"),
            None,
        ),
        (EventsAccountsReportInputs(), ("2026-03-01", "2026-03-08"), 7),
    ],
)
@patch("reports.events._shared.helpers.get_date_range")
def test_resolve_date_range(
    mock_get_date_range: MagicMock,
    inputs: EventsAccountsReportInputs,
    expected_dates: tuple[str, str],
    expected_days_call: int | None,
) -> None:
    if expected_days_call is not None:
        mock_get_date_range.return_value = expected_dates

    result = resolve_date_range(inputs)

    assert result == expected_dates
    if expected_days_call is None:
        mock_get_date_range.assert_not_called()
    else:
        mock_get_date_range.assert_called_once_with(expected_days_call)


@pytest.mark.unit
def test_extract_event_fields_with_complete_payload() -> None:
    event = {
        "event_id": "220",
        "event_name": "Role member changed",
        "service_name": "auth",
        "message": {
            "message": "Role updated",
            "timestamp": "2026-01-01T12:00:00Z",
            "instanceName": "privx-01",
            "remoteAddress": "10.0.0.1",
            "severity": "INFO",
            "audit-exposure": "internal",
            "SSH-PrivX-service": "events",
            "version": "1",
        },
    }

    fields = extract_event_fields(event)

    assert fields["event_id"] == "220"
    assert fields["event_name"] == "Role member changed"
    assert fields["message"] == "Role updated"
    assert fields["instance_name"] == "privx-01"
    assert fields["remote_address"] == "10.0.0.1"
    assert fields["service_name"] == "auth"


@pytest.mark.unit
def test_extract_event_fields_with_missing_message() -> None:
    fields = extract_event_fields({"event_id": "220"})

    assert fields["event_id"] == "220"
    assert fields["event_name"] == ""
    assert fields["message"] == ""
    assert fields["timestamp"] == ""
    assert fields["service_name"] == ""
