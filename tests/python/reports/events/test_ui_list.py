"""Tests for events UI list handler."""

from lib._report.generator import UIListResponse
from reports.events import get_list as events_get_list
from reports.events.query.ui import get_list as query_get_list


class TestEventsGetList:
    """Tests for events.get_list function (routing to subcommand)."""

    def test_routes_to_query_subcommand(self) -> None:
        """Should route to query subcommand for event_names."""
        result = events_get_list("query", "event_names")

        assert isinstance(result, UIListResponse)
        assert result.error_message is None
        assert len(result.values) > 0

    def test_returns_error_for_unknown_subcommand(self) -> None:
        """Should return error for unknown subcommand."""
        result = events_get_list("unknown_subcommand", "event_names")

        assert isinstance(result, UIListResponse)
        assert result.error_message is not None
        assert "Unknown subcommand" in result.error_message
        assert result.values == []

    def test_returns_error_for_subcommand_without_support(self) -> None:
        """Should return error for subcommand without UI list support."""
        result = events_get_list("accounts", "some_list")

        assert isinstance(result, UIListResponse)
        assert result.error_message is not None
        assert "does not support UI lists" in result.error_message
        assert result.values == []


class TestQueryGetList:
    """Tests for events/query/ui.get_list function."""

    def test_get_event_names_returns_list(self) -> None:
        """Should return list of event names for event_names key."""
        result = query_get_list("event_names")

        assert isinstance(result, UIListResponse)
        assert result.error_message is None
        assert isinstance(result.values, list)
        assert len(result.values) > 0

    def test_get_event_names_content_and_type(self) -> None:
        """Event names should include known values and be strings."""
        result = query_get_list("event_names")

        expected_events = ["Role-added", "Role-removed", "User-roles-modified"]
        for event in expected_events:
            assert event in result.values, f"Expected '{event}' in event names"
        assert all(isinstance(v, str) for v in result.values)

    def test_unknown_list_key_returns_error(self) -> None:
        """Should return error for unknown list key."""
        result = query_get_list("unknown_key")

        assert isinstance(result, UIListResponse)
        assert result.error_message is not None
        assert "Unknown list key" in result.error_message
        assert result.values == []

    def test_empty_list_key_returns_error(self) -> None:
        """Should return error for empty list key."""
        result = query_get_list("")

        assert isinstance(result, UIListResponse)
        assert result.error_message is not None
        assert result.values == []
