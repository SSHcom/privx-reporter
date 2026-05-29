"""Tests for ui/db/alt_group_queries.py."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from ui.db import alt_group_queries


@pytest.mark.unit
@patch("ui.db.alt_group_queries.use_database")
def test_list_alt_group_views_returns_ordered_views(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(1, "A View"), (2, "B View")]
    mock_result.keys.return_value = ["id", "name"]
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    result = alt_group_queries.list_alt_group_views()

    assert result == [{"id": 1, "name": "A View"}, {"id": 2, "name": "B View"}]


@pytest.mark.unit
@patch("ui.db.alt_group_queries.use_database")
def test_create_alt_group_view_success(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.fetchone.return_value = (10,)
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    success, message, view_id = alt_group_queries.create_alt_group_view("Dept View")

    assert success is True
    assert "Dept View" in message
    assert view_id == 10


@pytest.mark.unit
@patch("ui.db.alt_group_queries.use_database")
def test_create_alt_group_view_rejects_empty_name(mock_use_database: MagicMock) -> None:
    success, message, view_id = alt_group_queries.create_alt_group_view("   ")

    assert success is False
    assert "empty" in message.lower()
    assert view_id is None
    mock_use_database.assert_not_called()


@pytest.mark.unit
@patch("ui.db.alt_group_queries.use_database")
def test_create_alt_group_view_handles_duplicate_name(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(side_effect=IntegrityError("", "", ""))
    mock_use_database.return_value = mock_db

    success, message, view_id = alt_group_queries.create_alt_group_view("Existing")

    assert success is False
    assert "already exists" in message.lower()
    assert view_id is None


@pytest.mark.unit
@patch("ui.db.alt_group_queries.use_database")
def test_delete_alt_group_view_deleted_when_found(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    view_row = MagicMock()
    view_row.fetchone.return_value = (5,)
    mock_db.connection.execute.side_effect = [view_row, MagicMock(), MagicMock()]
    mock_use_database.return_value = mock_db

    result = alt_group_queries.delete_alt_group_view(5)

    assert result == "deleted"
    assert mock_db.connection.execute.call_count == 3


@pytest.mark.unit
@patch("ui.db.alt_group_queries.use_database")
def test_delete_alt_group_view_not_found(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    view_row = MagicMock()
    view_row.fetchone.return_value = None
    mock_db.connection.execute.return_value = view_row
    mock_use_database.return_value = mock_db

    result = alt_group_queries.delete_alt_group_view(999)

    assert result == "not_found"
    assert mock_db.connection.execute.call_count == 1


@pytest.mark.unit
@patch("ui.db.alt_group_queries.use_database")
def test_delete_alt_group_view_returns_error_on_exception(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(side_effect=Exception("DB failure"))
    mock_use_database.return_value = mock_db

    result = alt_group_queries.delete_alt_group_view(1)

    assert result == "error"


@pytest.mark.unit
@patch("ui.db.alt_group_queries.use_database")
def test_add_report_to_alt_group_success(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)
    mock_use_database.return_value = mock_db

    success, message = alt_group_queries.add_report_to_alt_group(
        alt_group_view_id=1,
        group_name="Critical",
        report_id=2,
    )

    assert success is True
    assert "saved" in message.lower()
    mock_db.connection.execute.assert_called_once()


@pytest.mark.unit
@patch("ui.db.alt_group_queries.use_database")
def test_add_report_to_alt_group_rejects_empty_group_name(mock_use_database: MagicMock) -> None:
    success, message = alt_group_queries.add_report_to_alt_group(
        alt_group_view_id=1,
        group_name="  ",
        report_id=2,
    )

    assert success is False
    assert "empty" in message.lower()
    mock_use_database.assert_not_called()


@pytest.mark.unit
@patch("ui.db.alt_group_queries.use_database")
def test_add_report_to_alt_group_duplicate(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(side_effect=IntegrityError("", "", ""))
    mock_use_database.return_value = mock_db

    success, message = alt_group_queries.add_report_to_alt_group(
        alt_group_view_id=1,
        group_name="Ops",
        report_id=2,
    )

    assert success is False
    assert "already assigned" in message.lower()


@pytest.mark.unit
@patch("ui.db.alt_group_queries.use_database")
def test_add_reports_to_alt_group_success(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)
    mock_use_database.return_value = mock_db

    success, message = alt_group_queries.add_reports_to_alt_group(
        alt_group_view_id=1,
        group_name="Ops",
        report_ids=[2, 4, 6],
    )

    assert success is True
    assert "saved" in message.lower()
    mock_db.connection.execute.assert_called_once()


@pytest.mark.unit
@patch("ui.db.alt_group_queries.use_database")
def test_add_reports_to_alt_group_rejects_empty_selection(mock_use_database: MagicMock) -> None:
    success, message = alt_group_queries.add_reports_to_alt_group(
        alt_group_view_id=1,
        group_name="Ops",
        report_ids=[],
    )

    assert success is False
    assert "at least one" in message.lower()
    mock_use_database.assert_not_called()


@pytest.mark.unit
@patch("ui.db.alt_group_queries.use_database")
def test_remove_report_from_alt_group_deletes_mapping(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)
    mock_use_database.return_value = mock_db

    alt_group_queries.remove_report_from_alt_group(7)

    mock_db.connection.execute.assert_called_once()


@pytest.mark.unit
@patch("ui.db.alt_group_queries.use_database")
def test_get_groups_for_view_returns_assignment_rows(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(11, "Ops", 3, "roles", "members")]
    mock_result.keys.return_value = [
        "id",
        "group_name",
        "report_id",
        "report_group_name",
        "report_name",
    ]
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    result = alt_group_queries.get_groups_for_view(1)

    assert result == [
        {
            "id": 11,
            "group_name": "Ops",
            "report_id": 3,
            "report_group_name": "roles",
            "report_name": "members",
        }
    ]


@pytest.mark.unit
@patch("ui.db.alt_group_queries.list_all_reports")
def test_list_reports_reuses_shared_report_query(mock_list_all_reports: MagicMock) -> None:
    mock_list_all_reports.return_value = [{"id": 1, "group_name": "access", "report_name": "hosts"}]

    result = alt_group_queries.list_reports()

    assert result == [{"id": 1, "group_name": "access", "report_name": "hosts"}]
    mock_list_all_reports.assert_called_once()
