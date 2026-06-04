from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lib import report_api
from ui.services.cache_service import get_cached_privx_client


def fetch_data() -> dict[str, Any]:
    """Fetch total defined target hosts from PrivX."""
    try:
        api = get_cached_privx_client()
    except Exception as exc:
        return {
            "label": "Total Defined Target Hosts",
            "description": "Live total count of target hosts defined in PrivX.",
            "total_defined_target_hosts": 0,
            "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "error": f"Failed to authenticate PrivX client: {exc}",
        }

    try:
        host_search = report_api.hosts.search_hosts(api, search_payload={}, offset=0, limit=1)
        total_hosts = int((host_search or {}).get("count", 0) or 0)
    except Exception as exc:
        return {
            "label": "Total Defined Target Hosts",
            "description": "Live total count of target hosts defined in PrivX.",
            "total_defined_target_hosts": 0,
            "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "error": f"Failed to query target hosts: {exc}",
        }

    return {
        "label": "Total Defined Target Hosts",
        "description": "Live total count of target hosts defined in PrivX.",
        "total_defined_target_hosts": total_hosts,
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
