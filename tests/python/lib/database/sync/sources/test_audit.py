"""Tests for audit sync source."""

from unittest.mock import MagicMock, patch

import pytest

from lib.database.sync.time_series.sources.audit import (
    AuditEventSync,
    _is_802_principal_modification_event,
    _normalize_modifications,
)


@pytest.mark.unit
def test_is_802_principal_modification_event_matches_valid_paths() -> None:
    event = {
        "event_id": "802",
        "message": {"modifications": {"Principals.0.Principal": {"old_value": "", "new_value": "root"}}},
    }
    assert _is_802_principal_modification_event(event) is True


@pytest.mark.unit
def test_is_802_principal_modification_event_rejects_malformed_json() -> None:
    event = {"event_id": "802", "message": {"modifications": "{invalid-json"}}
    assert _is_802_principal_modification_event(event) is False


@pytest.mark.unit
def test_normalize_modifications_keeps_invalid_json_unchanged() -> None:
    event = {"message": {"modifications": "{invalid-json"}}
    _normalize_modifications(event)
    assert event["message"]["modifications"] == "{invalid-json"


@pytest.mark.unit
@patch("lib.database.sync.time_series.sources.audit.report_api.get_audit_events")
def test_fetch_batch_uses_propagate_errors(mock_get_audit_events: MagicMock, mock_api: MagicMock) -> None:
    source = AuditEventSync()
    mock_get_audit_events.return_value = {"items": [{"id": "1"}], "count": 10}

    result = source.fetch_batch(
        api=mock_api,
        start_time="2026-01-01T00:00:00Z",
        end_time="2026-01-01T01:00:00Z",
        offset=5,
        limit=25,
    )

    assert result.count == 1
    assert len(result.items) == 1
    kwargs = mock_get_audit_events.call_args.kwargs
    assert kwargs["propagate_errors"] is True
    assert kwargs["offset"] == 5
    assert kwargs["limit"] == 25
