"""Admin database table models."""

from lib.database.models.admin.alt_group import AltGroupTable
from lib.database.models.admin.alt_group_view import AltGroupViewTable
from lib.database.models.admin.audit_event_sync_table import AuditEventSyncTable
from lib.database.models.admin.migration_history import MigrationHistoryTable
from lib.database.models.admin.report import ReportTable
from lib.database.models.admin.session import SessionTable
from lib.database.models.admin.user import UserTable
from lib.database.models.admin.user_group import UserGroupTable
from lib.database.models.admin.user_group_report import UserGroupReportTable

__all__ = [
    "AltGroupTable",
    "AltGroupViewTable",
    "AuditEventSyncTable",
    "MigrationHistoryTable",
    "ReportTable",
    "SessionTable",
    "UserGroupReportTable",
    "UserGroupTable",
    "UserTable",
]
