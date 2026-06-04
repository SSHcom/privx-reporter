import argparse
from typing import Any

from sqlalchemy import Select, select

from administration.event._shared import read_fixed_event_codes, use_admin_database
from lib.database.models.admin.audit_event_sync_table import AuditEventSyncTable


def _format_event_line(code: int, name: str, description: str, longest_name_len: int) -> str:
    padded_name = name.ljust(longest_name_len)
    return f"{code}\t{padded_name}\t{description}"


def _build_query(enabled: bool, disabled: bool, fixed: bool) -> Select:
    stmt = select(
        AuditEventSyncTable.c.code,
        AuditEventSyncTable.c.name,
        AuditEventSyncTable.c.description,
    ).order_by(AuditEventSyncTable.c.code)

    if fixed:
        fixed_codes = read_fixed_event_codes()
        if not fixed_codes:
            return stmt.where(AuditEventSyncTable.c.code.in_([-1]))
        return stmt.where(AuditEventSyncTable.c.code.in_(fixed_codes))

    if enabled:
        return stmt.where(AuditEventSyncTable.c.enabled.is_(True))

    if disabled:
        return stmt.where(AuditEventSyncTable.c.enabled.is_(False))

    return stmt


def handle_list_event(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, str | None]:
    """Handle event list action."""
    _ = config
    fixed = bool(getattr(args, "fixed", False))
    enabled = bool(getattr(args, "enabled", False))
    disabled = bool(getattr(args, "disabled", False))

    if enabled and disabled and not fixed:
        return {
            "error_message": "Use either --enabled or --disabled, not both.",
            "info_message": None,
        }

    db = use_admin_database()
    stmt = _build_query(enabled, disabled, fixed)
    rows = db.connection.execute(stmt).fetchall()
    longest_name_len = max((len(str(row.name)) for row in rows), default=0)

    for row in rows:
        print(_format_event_line(row.code, row.name, row.description, longest_name_len))

    if not rows:
        return {"error_message": None, "info_message": "No events found."}

    return {"error_message": None, "info_message": f"Listed {len(rows)} events."}
