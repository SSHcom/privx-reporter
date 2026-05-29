from unittest.mock import MagicMock, patch

import pytest

from reports._shared.user_group import _parse_access_groups, get_user_group, get_user_group_by_id


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (None, [""]),
        (123, [""]),
        ("", [""]),
        (" ", [""]),
        ("A, B", ["A", "B"]),
        ("A,,B", ["A", "B"]),
    ],
)
def test_parse_access_groups(raw_value: object, expected: list[str]) -> None:
    assert _parse_access_groups(raw_value) == expected


@pytest.mark.unit
@patch("reports._shared.user_group.use_database")
def test_get_user_group_blank_username_returns_none(mock_use_database: MagicMock) -> None:
    result = get_user_group("   ")

    assert result is None
    mock_use_database.assert_not_called()


@pytest.mark.unit
@patch("reports._shared.user_group.use_database")
def test_get_user_group_returns_resolved_group(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_use_database.return_value = mock_db
    mock_db.connection.execute.return_value.fetchone.return_value = (7, "Ops", "Default, Production")

    result = get_user_group("alice")

    assert result is not None
    assert result.id == 7
    assert result.name == "Ops"
    assert result.access_groups == ["Default", "Production"]


@pytest.mark.unit
@patch("reports._shared.user_group.use_database")
def test_get_user_group_unknown_user_returns_none(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_use_database.return_value = mock_db
    mock_db.connection.execute.return_value.fetchone.return_value = None

    result = get_user_group("unknown")

    assert result is None


@pytest.mark.unit
@patch("reports._shared.user_group.use_database")
def test_get_user_group_by_id_found(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_use_database.return_value = mock_db
    mock_db.connection.execute.return_value.fetchone.return_value = (9, "Restricted", "Default")

    result = get_user_group_by_id(9)

    assert result is not None
    assert result.id == 9
    assert result.name == "Restricted"
    assert result.access_groups == ["Default"]


@pytest.mark.unit
@patch("reports._shared.user_group.use_database")
def test_get_user_group_by_id_unknown_returns_none(mock_use_database: MagicMock) -> None:
    mock_db = MagicMock()
    mock_use_database.return_value = mock_db
    mock_db.connection.execute.return_value.fetchone.return_value = None

    result = get_user_group_by_id(999)

    assert result is None
