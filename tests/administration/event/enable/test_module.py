"""Tests for event enable administration command."""

import argparse
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
@patch("administration.event.enable.module.use_admin_database")
@patch("administration.event.enable.module.read_fixed_event_codes", return_value=set())
def test_enable_event_success_executes_expected_update(
    _mock_fixed: MagicMock,
    mock_use_admin_database: MagicMock,
) -> None:
    """Enable should update by code and commit once."""
    from administration.event.enable.module import handle_enable_event

    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_db = MagicMock()
    mock_db.connection.execute.return_value = mock_result
    mock_use_admin_database.return_value = mock_db

    result = handle_enable_event(argparse.Namespace(subcommand="enable", code="201"), {})

    assert result == {"error_message": None, "info_message": "Event code '201' enabled."}
    mock_db.connection.commit.assert_called_once()

    stmt = mock_db.connection.execute.call_args[0][0]
    compiled_sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "WHERE audit_event_sync.code = 201" in compiled_sql
    assert "enabled=true" in compiled_sql


@pytest.mark.unit
@patch("administration.event.enable.module.use_admin_database")
@patch("administration.event.enable.module.read_fixed_event_codes", return_value=set())
def test_enable_event_not_found_returns_error(
    _mock_fixed: MagicMock,
    mock_use_admin_database: MagicMock,
) -> None:
    from administration.event.enable.module import handle_enable_event

    mock_result = MagicMock()
    mock_result.rowcount = 0
    mock_db = MagicMock()
    mock_db.connection.execute.return_value = mock_result
    mock_use_admin_database.return_value = mock_db

    result = handle_enable_event(argparse.Namespace(subcommand="enable", code="999"), {})
    assert result == {"error_message": "Event code '999' not found.", "info_message": None}


@pytest.mark.unit
@patch("administration.event.enable.module.use_admin_database")
@patch("administration.event.enable.module.read_fixed_event_codes", return_value={201})
def test_enable_event_fixed_code_is_not_changed(
    _mock_fixed: MagicMock,
    mock_use_admin_database: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from administration.event.enable.module import handle_enable_event

    result = handle_enable_event(argparse.Namespace(subcommand="enable", code="201"), {})

    assert result == {"error_message": None, "info_message": None}
    mock_use_admin_database.assert_not_called()
    assert "Cannot change event code 201" in capsys.readouterr().out


@pytest.mark.unit
@patch("administration.event.enable.module.use_admin_database")
@patch("administration.event.enable.module.read_fixed_event_codes", return_value=set())
def test_enable_event_invalid_code_raises_value_error(
    _mock_fixed: MagicMock,
    _mock_use_admin_database: MagicMock,
) -> None:
    from administration.event.enable.module import handle_enable_event

    with pytest.raises(ValueError):
        handle_enable_event(argparse.Namespace(subcommand="enable", code="not-a-number"), {})
