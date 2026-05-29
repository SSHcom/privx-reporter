"""Shared access-group resolution helpers for reports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lib import report_api
from reports._shared.user_group import get_user_group_by_id

if TYPE_CHECKING:
    import privx_api


def resolve_allowed_access_group_ids(
    api: privx_api.PrivXAPI,
    user_group_id: str,
) -> tuple[set[str] | None, str | None]:
    """Resolve configured access-group names to PrivX access-group IDs.

    Returns:
        Tuple of (allowed_access_group_ids, error_message).
        - allowed_access_group_ids is None when resolution fails.
        - error_message is None on success.
    """
    try:
        parsed_user_group_id = int(user_group_id)
    except (TypeError, ValueError):
        return None, f"Invalid user group id: {user_group_id}"

    user_group = get_user_group_by_id(parsed_user_group_id)

    if user_group is None:
        return None, f"User group with ID {parsed_user_group_id} not found"

    access_groups_response = report_api.access_group.search_access_groups(api)

    if access_groups_response is None:
        return None, "Failed to resolve access groups from PrivX API"

    name_to_id_map: dict[str, str] = {}

    for access_group in access_groups_response.get("items", []):
        access_group_name = access_group.get("name")
        access_group_id = access_group.get("id")

        if isinstance(access_group_name, str) and isinstance(access_group_id, str):
            normalized_name = access_group_name.strip().lower()

            if normalized_name:
                name_to_id_map[normalized_name] = access_group_id

    allowed_access_group_ids: set[str] = set()
    empty_names: list[str] = []
    unresolved_names: list[str] = []

    for access_group_name in user_group.access_groups:
        normalized_name = access_group_name.strip().lower()

        if not normalized_name:
            empty_names.append(access_group_name)
            continue

        resolved_id = name_to_id_map.get(normalized_name)

        if resolved_id is None:
            unresolved_names.append(access_group_name)
            continue

        allowed_access_group_ids.add(resolved_id)

    if empty_names:
        return None, f"Permission denied: User group '{user_group.name}' has no access group in its configuration."

    if unresolved_names:
        unresolved_display = ", ".join(f"'{name}'" for name in unresolved_names)
        return (
            None,
            f"Permission denied: User group '{user_group.name}' contains unknown access groups: {unresolved_display}",
        )

    return allowed_access_group_ids, None
