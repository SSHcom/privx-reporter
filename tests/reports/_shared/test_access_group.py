from unittest.mock import MagicMock, patch

import pytest

from reports._shared.access_group import resolve_allowed_access_group_ids
from reports._shared.user_group import UserGroup


@pytest.mark.unit
@patch("reports._shared.access_group.get_user_group_by_id")
def test_resolve_allowed_access_group_ids_invalid_user_group_id(
    mock_get_user_group_by_id: MagicMock,
) -> None:
    """Resolver should return error for non-integer user_group_id."""
    api = MagicMock()
    result, error = resolve_allowed_access_group_ids(api, "abc")

    assert result is None
    assert error == "Invalid user group id: abc"
    mock_get_user_group_by_id.assert_not_called()


@pytest.mark.unit
@patch("reports._shared.access_group.report_api")
@patch("reports._shared.access_group.get_user_group_by_id")
def test_resolve_allowed_access_group_ids_success(
    mock_get_user_group_by_id: MagicMock,
    mock_report_api: MagicMock,
) -> None:
    """Resolver should map configured access-group names to IDs."""
    api = MagicMock()
    mock_get_user_group_by_id.return_value = UserGroup(
        id=3,
        name="Ops",
        access_groups=["Default", "Production"],
    )
    mock_report_api.access_group.search_access_groups.return_value = {
        "items": [
            {"id": "ag-default", "name": "Default"},
            {"id": "ag-prod", "name": "Production"},
        ]
    }

    result, error = resolve_allowed_access_group_ids(api, "3")

    assert error is None
    assert result == {"ag-default", "ag-prod"}


@pytest.mark.unit
@patch("reports._shared.access_group.report_api")
@patch("reports._shared.access_group.get_user_group_by_id")
def test_resolve_allowed_access_group_ids_unknown_name_fails(
    mock_get_user_group_by_id: MagicMock,
    mock_report_api: MagicMock,
) -> None:
    """Resolver should fail when any configured access-group name is unknown."""
    api = MagicMock()
    mock_get_user_group_by_id.return_value = UserGroup(
        id=4,
        name="Restricted",
        access_groups=["Default", "Missing"],
    )
    mock_report_api.access_group.search_access_groups.return_value = {
        "items": [
            {"id": "ag-default", "name": "Default"},
        ]
    }

    result, error = resolve_allowed_access_group_ids(api, "4")

    assert result is None
    assert error == "Permission denied: User group 'Restricted' contains unknown access groups: 'Missing'"


@pytest.mark.unit
@patch("reports._shared.access_group.report_api")
@patch("reports._shared.access_group.get_user_group_by_id")
def test_resolve_allowed_access_group_ids_empty_name_fails_with_no_access_group_message(
    mock_get_user_group_by_id: MagicMock,
    mock_report_api: MagicMock,
) -> None:
    """Resolver should fail with no-access-group message for empty configured names."""
    api = MagicMock()
    mock_get_user_group_by_id.return_value = UserGroup(
        id=5,
        name="NoAccess",
        access_groups=[""],
    )
    mock_report_api.access_group.search_access_groups.return_value = {
        "items": [
            {"id": "ag-default", "name": "Default"},
        ]
    }

    result, error = resolve_allowed_access_group_ids(api, "5")

    assert result is None
    assert error == "Permission denied: User group 'NoAccess' has no access group in its configuration."


@pytest.mark.unit
@patch("reports._shared.access_group.get_user_group_by_id")
def test_resolve_allowed_access_group_ids_unknown_user_group(
    mock_get_user_group_by_id: MagicMock,
) -> None:
    api = MagicMock()
    mock_get_user_group_by_id.return_value = None

    result, error = resolve_allowed_access_group_ids(api, "77")

    assert result is None
    assert error == "User group with ID 77 not found"


@pytest.mark.unit
@patch("reports._shared.access_group.report_api")
@patch("reports._shared.access_group.get_user_group_by_id")
def test_resolve_allowed_access_group_ids_access_group_search_failure(
    mock_get_user_group_by_id: MagicMock,
    mock_report_api: MagicMock,
) -> None:
    api = MagicMock()
    mock_get_user_group_by_id.return_value = UserGroup(
        id=6,
        name="Ops",
        access_groups=["Default"],
    )
    mock_report_api.access_group.search_access_groups.return_value = None

    result, error = resolve_allowed_access_group_ids(api, "6")

    assert result is None
    assert error == "Failed to resolve access groups from PrivX API"
