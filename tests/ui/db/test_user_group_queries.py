"""Tests for ui/db/user_group_queries.py."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from ui.db import user_group_queries


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_list_user_groups_returns_ordered_groups(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(2, "Beta"), (1, "Alpha")]
    mock_result.keys.return_value = ["id", "name"]
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    result = user_group_queries.list_user_groups()

    assert len(result) == 2
    assert result[0] == {"id": 2, "name": "Beta"}
    assert result[1] == {"id": 1, "name": "Alpha"}


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_list_reports_returns_ordered_by_group_and_name(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        (1, "Access", "Hosts"),
        (2, "Access", "Users"),
        (3, "Events", "Audit"),
    ]
    mock_result.keys.return_value = ["id", "group_name", "report_name"]
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    result = user_group_queries.list_reports()

    assert len(result) == 3
    assert result[0]["group_name"] == "Access"
    assert result[0]["report_name"] == "Hosts"


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_get_report_ids_for_group_returns_set(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(1,), (3,), (5,)]
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    result = user_group_queries.get_report_ids_for_group(user_group_id=1)

    assert result == {1, 3, 5}


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_get_report_ids_for_group_returns_empty_set_when_none(
    mock_use_database: MagicMock,
) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    result = user_group_queries.get_report_ids_for_group(user_group_id=999)

    assert result == set()


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_include_report_in_group_inserts_when_not_exists(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_db.connection.execute.return_value.fetchone.return_value = None
    mock_use_database.return_value = mock_db

    user_group_queries.include_report_in_group(user_group_id=1, report_id=5)

    assert mock_db.connection.execute.call_count == 2


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_include_report_in_group_is_idempotent_when_exists(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_db.connection.execute.return_value.fetchone.return_value = (1,)
    mock_use_database.return_value = mock_db

    user_group_queries.include_report_in_group(user_group_id=1, report_id=5)

    assert mock_db.connection.execute.call_count == 1


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_exclude_report_from_group_deletes_mapping(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)
    mock_use_database.return_value = mock_db

    user_group_queries.exclude_report_from_group(user_group_id=1, report_id=5)

    mock_db.connection.execute.assert_called_once()


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_create_user_group_success(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.fetchone.return_value = (42,)
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    success, message, group_id = user_group_queries.create_user_group("Test Group")

    assert success is True
    assert "Test Group" in message
    assert group_id == 42
    insert_params = mock_db.connection.execute.call_args_list[0].args[1]
    assert insert_params["access_groups"] == "Default"


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_create_user_group_strips_whitespace(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.fetchone.return_value = (1,)
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    success, message, _ = user_group_queries.create_user_group("  Spaced Name  ")

    assert success is True
    assert "Spaced Name" in message
    insert_params = mock_db.connection.execute.call_args_list[0].args[1]
    assert insert_params["access_groups"] == "Default"


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_create_user_group_appends_default_to_custom_access_groups(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.fetchone.return_value = (11,)
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    success, _message, _group_id = user_group_queries.create_user_group(
        "Ops Group",
        access_groups="Production,Staging",
    )

    assert success is True
    insert_params = mock_db.connection.execute.call_args_list[0].args[1]
    assert insert_params["access_groups"] == "Production,Staging,Default"


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_create_user_group_keeps_admin_group_access_groups_null(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    mock_result = MagicMock()
    mock_result.fetchone.return_value = (1,)
    mock_db.connection.execute.return_value = mock_result
    mock_use_database.return_value = mock_db

    success, _message, _group_id = user_group_queries.create_user_group(
        "admin",
        access_groups="Default,Production",
    )

    assert success is True
    insert_params = mock_db.connection.execute.call_args_list[0].args[1]
    assert insert_params["access_groups"] is None


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_create_user_group_rejects_empty_name(mock_use_database: MagicMock) -> None:
    success, message, group_id = user_group_queries.create_user_group("")

    assert success is False
    assert "empty" in message.lower()
    assert group_id is None
    mock_use_database.assert_not_called()


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_create_user_group_rejects_whitespace_only_name(mock_use_database: MagicMock) -> None:
    success, message, group_id = user_group_queries.create_user_group("   ")

    assert success is False
    assert "empty" in message.lower()
    assert group_id is None
    mock_use_database.assert_not_called()


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_create_user_group_handles_duplicate_name(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(side_effect=IntegrityError("", "", ""))
    mock_use_database.return_value = mock_db

    success, message, group_id = user_group_queries.create_user_group("Existing Group")

    assert success is False
    assert "already exists" in message.lower()
    assert group_id is None


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_get_viewable_report_names_returns_reports_for_user(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    user_result = MagicMock()
    user_result.fetchone.return_value = (2,)

    report_result = MagicMock()
    report_result.fetchall.return_value = [
        ("Access", "Hosts"),
        ("Access", "Users"),
    ]

    mock_db.connection.execute.side_effect = [user_result, report_result]
    mock_use_database.return_value = mock_db

    result = user_group_queries.get_viewable_report_names("testuser")

    assert len(result) == 2
    assert result[0] == ("Access", "Hosts")
    assert result[1] == ("Access", "Users")


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_get_viewable_report_names_returns_empty_for_unknown_user(
    mock_use_database: MagicMock,
) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    user_result = MagicMock()
    user_result.fetchone.return_value = None
    mock_db.connection.execute.return_value = user_result
    mock_use_database.return_value = mock_db

    result = user_group_queries.get_viewable_report_names("nonexistent")

    assert result == []


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_get_viewable_report_names_returns_empty_for_empty_username(
    mock_use_database: MagicMock,
) -> None:
    result = user_group_queries.get_viewable_report_names("")

    assert result == []
    mock_use_database.assert_not_called()


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_delete_user_group_returns_deleted_when_no_users_assigned(
    mock_use_database: MagicMock,
) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    group_row = MagicMock()
    group_row.fetchone.return_value = (1,)
    assigned_count = MagicMock()
    assigned_count.scalar.return_value = 0

    mock_db.connection.execute.side_effect = [group_row, assigned_count, MagicMock(), MagicMock()]
    mock_use_database.return_value = mock_db

    result = user_group_queries.delete_user_group(1)

    assert result == "deleted"


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_delete_user_group_returns_blocked_when_users_assigned(
    mock_use_database: MagicMock,
) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    group_row = MagicMock()
    group_row.fetchone.return_value = (1,)
    assigned_count = MagicMock()
    assigned_count.scalar.return_value = 2

    mock_db.connection.execute.side_effect = [group_row, assigned_count]
    mock_use_database.return_value = mock_db

    result = user_group_queries.delete_user_group(1)

    assert result == "blocked_due_to_assignments"
    assert mock_db.connection.execute.call_count == 2


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_delete_user_group_returns_not_found_for_missing_group(
    mock_use_database: MagicMock,
) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    group_row = MagicMock()
    group_row.fetchone.return_value = None
    mock_db.connection.execute.return_value = group_row
    mock_use_database.return_value = mock_db

    result = user_group_queries.delete_user_group(999)

    assert result == "not_found"
    assert mock_db.connection.execute.call_count == 1


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_delete_user_group_returns_error_on_exception(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(side_effect=Exception("DB failure"))
    mock_use_database.return_value = mock_db

    result = user_group_queries.delete_user_group(1)

    assert result == "error"


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_delete_user_group_removes_report_mappings_before_group(
    mock_use_database: MagicMock,
) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    group_row = MagicMock()
    group_row.fetchone.return_value = (5,)
    assigned_count = MagicMock()
    assigned_count.scalar.return_value = 0
    delete_mappings_result = MagicMock()
    delete_group_result = MagicMock()

    mock_db.connection.execute.side_effect = [group_row, assigned_count, delete_mappings_result, delete_group_result]
    mock_use_database.return_value = mock_db

    result = user_group_queries.delete_user_group(5)

    assert result == "deleted"
    assert mock_db.connection.execute.call_count == 4


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_get_viewable_report_names_returns_empty_for_none_username(
    mock_use_database: MagicMock,
) -> None:
    result = user_group_queries.get_viewable_report_names(None)  # type: ignore[arg-type]

    assert result == []
    mock_use_database.assert_not_called()


@pytest.mark.unit
@patch("ui.db.user_group_queries.use_database")
def test_get_viewable_report_names_returns_empty_when_no_reports_mapped(
    mock_use_database: MagicMock,
) -> None:
    mock_db = MagicMock()
    mock_db.connection.begin().__enter__ = MagicMock(return_value=MagicMock())
    mock_db.connection.begin().__exit__ = MagicMock(return_value=None)

    user_result = MagicMock()
    user_result.fetchone.return_value = (3,)

    report_result = MagicMock()
    report_result.fetchall.return_value = []

    mock_db.connection.execute.side_effect = [user_result, report_result]
    mock_use_database.return_value = mock_db

    result = user_group_queries.get_viewable_report_names("user_with_no_reports")

    assert result == []
