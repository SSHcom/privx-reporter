from typing import TYPE_CHECKING, Any

from lib.utils.date import get_date_range

if TYPE_CHECKING:
    from reports.events._shared.models import (
        EventsAccountsReportInputs,
        EventsQueryReportInputs,
        EventsRoleMembersReportInputs,
    )


def resolve_date_range(
    inputs: "EventsQueryReportInputs | EventsRoleMembersReportInputs | EventsAccountsReportInputs",
) -> tuple[str, str]:
    if inputs.days:
        from_date, to_date = get_date_range(int(inputs.days))
    elif inputs.from_date and inputs.to_date:
        from_date = inputs.from_date
        to_date = inputs.to_date
    else:
        from_date, to_date = get_date_range(7)
    return from_date, to_date


def extract_event_fields(event: dict[str, Any]) -> dict[str, Any]:
    message = event.get("message", {})
    return {
        "event_id": event.get("event_id", ""),
        "event_name": event.get("event_name", ""),
        "message": message.get("message", ""),
        "timestamp": message.get("timestamp", ""),
        "instance_name": message.get("instanceName", ""),
        "remote_address": message.get("remoteAddress", ""),
        "severity": message.get("severity", ""),
        "service_name": event.get("service_name", ""),
        "audit_exposure": message.get("audit-exposure", ""),
        "ssh_privx_service": message.get("SSH-PrivX-service", ""),
        "version": message.get("version", ""),
    }
