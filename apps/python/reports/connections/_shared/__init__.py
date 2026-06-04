"""Shared utilities for connections reports."""

from typing import Any

from reports.connections._shared.models import (
    DetailsReportInputs as DetailsReportInputs,
)
from reports.connections._shared.models import (
    QueryReportInputs as QueryReportInputs,
)


def extract_target_ips(dst_list: list[dict[str, Any]] | None) -> str:
    """Extract target IPs from dst list, with ranges taking precedence over individual IPs.

    Args:
        dst_list: List of dst entries from target_network_data

    Returns:
        CSV string of target IPs (ranges first, then individual IPs not matching range endpoints)
    """
    if not dst_list:
        return ""

    ranges: list[str] = []
    individual_ips: list[str] = []
    seen: set[str] = set()

    for dst in dst_list:
        ip_data = dst.get("selector", {}).get("ip", {})
        start_ip = ip_data.get("start", "")
        end_ip = ip_data.get("end", "")

        if not start_ip:
            continue

        if end_ip and end_ip != start_ip:
            ip_range = f"{start_ip}-{end_ip}"
            if ip_range not in seen:
                seen.add(ip_range)
                ranges.append(ip_range)
                seen.add(start_ip)
                seen.add(end_ip)
        elif start_ip not in seen:
            seen.add(start_ip)
            individual_ips.append(start_ip)

    return ", ".join(ranges + individual_ips)
