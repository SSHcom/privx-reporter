"""Helper functions for role report processing."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import privx_api

from lib.report_api.access_group import get_access_group_by_id

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


def extract_role_restrictions(role: dict[str, Any]) -> dict[str, str]:
    """
    Extract contextual restriction fields from a role.

    Args:
        role: Role dictionary from the PrivX API

    Returns:
        Dictionary with restriction fields suitable for output:
        - block_role: Boolean converted to string
        - validity: Comma-separated list of validity days
        - start_time: Start time string
        - end_time: End time string
        - timezone: Timezone string
        - ip_masks: Comma-separated list of IP masks
    """
    context = role.get("context", {})

    # Extract context fields with defaults
    block_role = context.get("block_role", False)
    validity = context.get("validity", [])
    start_time = context.get("start_time", "")
    end_time = context.get("end_time", "")
    timezone = context.get("timezone", "")
    ip_masks = context.get("ip_masks", [])

    return {
        "block_role": str(block_role),
        "validity": ",".join(validity) if validity else "",
        "start_time": start_time,
        "end_time": end_time,
        "timezone": timezone,
        "ip_masks": ",".join(ip_masks) if ip_masks else "",
    }


def fetch_access_group_details(api: "privx_api.PrivXAPI", access_group_id: str) -> dict[str, Any]:
    """
    Fetch access group details and return formatted fields.

    Args:
        api: PrivX API client instance
        access_group_id: Access group ID to fetch

    Returns:
        Dictionary with access_group_name, access_group_comment, and access_group_default fields
    """
    if not access_group_id:
        return {
            "access_group_name": "",
            "access_group_comment": "",
            "access_group_default": False,
        }

    access_group = get_access_group_by_id(api, access_group_id)
    if access_group:
        return {
            "access_group_name": access_group.get("name", ""),
            "access_group_comment": access_group.get("comment", ""),
            "access_group_default": access_group.get("default", False),
        }

    return {
        "access_group_name": "",
        "access_group_comment": "",
        "access_group_default": False,
    }
