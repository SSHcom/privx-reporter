from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from lib.report_api._shared import get_response_data
from ui.services.cache_service import get_cached_privx_client

_EXPIRING_DAYS = 30
_RECENTLY_EXPIRED_DAYS = 7


def fetch_certificate_data() -> dict[str, Any]:
    """Fetch PrivX certificates and return expiry info and status breakdown."""
    now = datetime.now(UTC)
    expiry_cutoff = now + timedelta(days=_EXPIRING_DAYS)
    expired_cutoff = now - timedelta(days=_RECENTLY_EXPIRED_DAYS)

    base_result: dict[str, Any] = {
        "label": "PrivX Certificate Status",
        "description": (
            f"Certificates expiring within {_EXPIRING_DAYS} days "
            f"or expired within the last {_RECENTLY_EXPIRED_DAYS} days."
        ),
        "expiring_soon": [],
        "recently_expired": [],
        "status_breakdown": {},
        "total_certificates": 0,
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    try:
        api = get_cached_privx_client()
    except Exception as exc:
        return {**base_result, "error": f"Failed to connect to PrivX: {exc}"}

    try:
        resp = api.get_certificates_list()
        data = get_response_data(resp, "get_certificates_list")
    except Exception as exc:
        return {**base_result, "error": f"Failed to fetch certificates: {exc}"}

    if data is None:
        return {**base_result, "error": "No certificate data returned"}

    items = data.get("items", [])
    base_result["total_certificates"] = len(items)

    # Status breakdown
    status_counts: dict[str, int] = {}
    expiring_soon: list[dict[str, str]] = []
    recently_expired: list[dict[str, str]] = []

    for cert in items:
        status = cert.get("status", "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1

        # Skip revoked certs
        if status == "CERT_REVOKED":
            continue

        not_after_str = cert.get("not_after", "")
        if not not_after_str:
            continue

        try:
            not_after = datetime.fromisoformat(not_after_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        subject = cert.get("subject", "")
        issuer = cert.get("issuer", "")
        cert_type = cert.get("type", "")

        if now <= not_after <= expiry_cutoff:
            # Expiring within 30 days
            days_left = max(0, int((not_after - now).total_seconds() // 86400))
            expiring_soon.append(
                {
                    "Subject": subject,
                    "Issuer": issuer,
                    "Type": cert_type,
                    "Expires": not_after.strftime("%Y-%m-%d %H:%M UTC"),
                    "Days Left": str(days_left),
                }
            )
        elif expired_cutoff <= not_after < now:
            # Expired within last 7 days
            days_ago = max(0, int((now - not_after).total_seconds() // 86400))
            recently_expired.append(
                {
                    "Subject": subject,
                    "Issuer": issuer,
                    "Type": cert_type,
                    "Expired": not_after.strftime("%Y-%m-%d %H:%M UTC"),
                    "Days Ago": str(days_ago),
                }
            )

    # Sort by urgency
    expiring_soon.sort(key=lambda r: int(r["Days Left"]))
    recently_expired.sort(key=lambda r: int(r["Days Ago"]))

    return {
        **base_result,
        "expiring_soon": expiring_soon,
        "recently_expired": recently_expired,
        "status_breakdown": status_counts,
        "updated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
