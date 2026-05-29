from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lib import report_api
from ui.services.cache_service import get_cached_privx_client


def fetch_data() -> dict[str, Any]:
    """Fetch total defined network targets from PrivX inventory."""
    base_result: dict[str, Any] = {
        "label": "Total Defined Network Targets",
        "description": "Live total count of network targets defined in PrivX.",
        "total_defined_network_targets": 0,
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    try:
        api = get_cached_privx_client()
    except Exception as exc:
        return {
            **base_result,
            "error": f"Failed to authenticate PrivX client: {exc}",
        }

    try:
        network_targets = report_api.network_targets.get_all_network_targets(api)
    except Exception as exc:
        return {
            **base_result,
            "error": f"Failed to query network targets: {exc}",
        }

    return {
        **base_result,
        "total_defined_network_targets": len(network_targets),
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
