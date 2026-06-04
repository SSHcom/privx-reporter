"""Tests for event list administration command."""

import argparse
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
@patch("administration.event.list.module.use_admin_database")
def test_list_no_events(mock_use_admin_database: MagicMock) -> None:
    """Returns info message when no events found."""
    mock_db = MagicMock()
    mock_db.connection.execute.return_value.fetchall.return_value = []
    mock_use_admin_database.return_value = mock_db

    from administration.event.list.module import handle_list_event

    mock_config: dict[str, object] = {}
    mock_args = argparse.Namespace(subcommand="list", enabled=False, disabled=False, fixed=False)

    result = handle_list_event(mock_args, mock_config)

    assert result == {"error_message": None, "info_message": "No events found."}


@pytest.mark.unit
@patch("administration.event.list.module.use_admin_database")
def test_list_with_events(mock_use_admin_database: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    """Lists events and returns count."""
    mock_row = MagicMock()
    mock_row.code = 201
    mock_row.name = "AUDIT_EVENT"
    mock_row.description = "Test event"

    mock_db = MagicMock()
    mock_db.connection.execute.return_value.fetchall.return_value = [mock_row]
    mock_use_admin_database.return_value = mock_db

    from administration.event.list.module import handle_list_event

    mock_config: dict[str, object] = {}
    mock_args = argparse.Namespace(subcommand="list", enabled=False, disabled=False, fixed=False)

    result = handle_list_event(mock_args, mock_config)

    assert result == {"error_message": None, "info_message": "Listed 1 events."}
    captured = capsys.readouterr()
    assert "201" in captured.out
    assert "AUDIT_EVENT" in captured.out


@pytest.mark.unit
def test_list_enabled_and_disabled_conflict() -> None:
    """Returns error when both --enabled and --disabled are used."""
    from administration.event.list.module import handle_list_event

    mock_config: dict[str, object] = {}
    mock_args = argparse.Namespace(subcommand="list", enabled=True, disabled=True, fixed=False)

    result = handle_list_event(mock_args, mock_config)

    assert result == {
        "error_message": "Use either --enabled or --disabled, not both.",
        "info_message": None,
    }


@pytest.mark.unit
@patch("administration.event.list.module.read_fixed_event_codes", return_value={201, 202})
@patch("administration.event.list.module.use_admin_database")
def test_list_fixed_mode(mock_use_admin_database: MagicMock, _mock_read_fixed_codes: MagicMock) -> None:
    """Fixed mode queries by fixed event codes."""
    mock_db = MagicMock()
    mock_db.connection.execute.return_value.fetchall.return_value = []
    mock_use_admin_database.return_value = mock_db

    from administration.event.list.module import handle_list_event

    mock_config: dict[str, object] = {}
    mock_args = argparse.Namespace(subcommand="list", enabled=True, disabled=True, fixed=True)

    result = handle_list_event(mock_args, mock_config)

    assert result["error_message"] is None
    assert result["info_message"] == "No events found."


@pytest.mark.unit
@pytest.mark.parametrize(
    ("enabled", "disabled", "fixed", "fixed_codes", "sql_fragment"),
    [
        (True, False, False, {201, 202}, "audit_event_sync.enabled IS true"),
        (False, True, False, {201, 202}, "audit_event_sync.enabled IS false"),
        (False, False, True, {201, 202}, "audit_event_sync.code IN (201, 202)"),
        (False, False, True, set(), "audit_event_sync.code IN (-1)"),
    ],
)
@patch("administration.event.list.module.read_fixed_event_codes")
def test_build_query_branching(
    mock_read_fixed_event_codes: MagicMock,
    enabled: bool,
    disabled: bool,
    fixed: bool,
    fixed_codes: set[int],
    sql_fragment: str,
) -> None:
    """_build_query should pick the expected filter branch."""
    from administration.event.list.module import _build_query

    mock_read_fixed_event_codes.return_value = fixed_codes
    stmt = _build_query(enabled=enabled, disabled=disabled, fixed=fixed)
    compiled_sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))

    assert sql_fragment in compiled_sql
