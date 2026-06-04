"""Tests for generator UI list retrieval."""

from lib._report.generator import UIListResponse, get_list


class TestGetList:
    """Tests for get_list function."""

    def test_get_list_valid_command_subcommand_and_key(self) -> None:
        """Should return list values for valid command, subcommand, and list key."""
        result = get_list("events", "query", "event_names")

        assert isinstance(result, UIListResponse)
        assert result.error_message is None
        assert isinstance(result.values, list)
        assert len(result.values) > 0
        assert all(isinstance(v, str) for v in result.values)

    def test_get_list_invalid_command(self) -> None:
        """Should return error for invalid command."""
        result = get_list("invalid_command", "query", "some_list")

        assert isinstance(result, UIListResponse)
        assert result.error_message is not None
        assert "Invalid report type" in result.error_message
        assert result.values == []

    def test_get_list_invalid_subcommand(self) -> None:
        """Should return error for invalid subcommand."""
        result = get_list("events", "invalid_subcommand", "some_list")

        assert isinstance(result, UIListResponse)
        assert result.error_message is not None
        assert "Unknown subcommand" in result.error_message
        assert result.values == []

    def test_get_list_subcommand_without_list_support(self) -> None:
        """Should return error for subcommand that doesn't support UI lists."""
        # "accounts" subcommand doesn't have list retrieval implemented
        result = get_list("events", "accounts", "some_list")

        assert isinstance(result, UIListResponse)
        assert result.error_message is not None
        assert "does not support UI lists" in result.error_message
        assert result.values == []

    def test_get_list_unknown_list_key(self) -> None:
        """Should return error for unknown list key."""
        result = get_list("events", "query", "unknown_list_key")

        assert isinstance(result, UIListResponse)
        assert result.error_message is not None
        assert "Unknown list key" in result.error_message
        assert result.values == []


class TestUIListResponse:
    """Tests for UIListResponse dataclass."""

    def test_default_error_message_is_none(self) -> None:
        """Should have None as default error_message."""
        response = UIListResponse(values=["a", "b"])

        assert response.values == ["a", "b"]
        assert response.error_message is None

    def test_can_set_error_message(self) -> None:
        """Should allow setting error_message."""
        response = UIListResponse(values=[], error_message="Some error")

        assert response.values == []
        assert response.error_message == "Some error"
