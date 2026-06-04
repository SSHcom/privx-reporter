from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lib import report_api
from ui.services.cache_service import get_cached_privx_client


def fetch_data() -> dict[str, Any]:
    """Fetch total defined target accounts from PrivX hosts principals."""
    base_result = {
        "label": "Total Defined Target Accounts",
        "description": "Live total count of unique target accounts defined on PrivX hosts.",
        "total_defined_target_accounts": 0,
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
        hosts = report_api.hosts.get_all_hosts(api)
    except Exception as exc:
        return {
            **base_result,
            "error": f"Failed to query target hosts: {exc}",
        }

    unique_accounts: set[str] = set()
    for host in hosts:
        for principal in host.get("principals", []) or []:
            account_name = str((principal or {}).get("principal", "")).strip()
            if account_name:
                unique_accounts.add(account_name.lower())

    return {
        **base_result,
        "total_defined_target_accounts": len(unique_accounts),
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
