import argparse
from typing import Any

from sqlalchemy import update

from administration.event._shared import read_fixed_event_codes, use_admin_database
from lib.database.models.admin.audit_event_sync_table import AuditEventSyncTable


def handle_enable_event(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, str | None]:
    """Handle event enable action."""
    _ = config

    code = int(args.code)
    fixed_codes = read_fixed_event_codes()

    if code in fixed_codes:
        print(f"Cannot change event code {code}: it is on the fixed list.")
        return {"error_message": None, "info_message": None}

    db = use_admin_database()
    stmt = update(AuditEventSyncTable).where(AuditEventSyncTable.c.code == code).values(enabled=True)
    result = db.connection.execute(stmt)
    db.connection.commit()

    if result.rowcount == 0:
        return {"error_message": f"Event code '{code}' not found.", "info_message": None}

    return {"error_message": None, "info_message": f"Event code '{code}' enabled."}
