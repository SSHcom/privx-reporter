"""Tests are not necessary for this module."""

from lib.database.models.admin.audit_event_sync_table import AuditEventSyncTable
from lib.database.models.admin.migration_history import MigrationHistoryTable
from lib.database.models.admin.report import ReportTable
from lib.database.models.admin.user import UserTable
from lib.database.models.admin.user_group import UserGroupTable
from lib.database.models.admin.user_group_report import UserGroupReportTable
from lib.database.models.meta import admin_db_metadata, data_db_metadata
from lib.database.models.sync.audit_event import AuditEventTable
from lib.database.models.sync.connection import ConnectionTable

__all__ = [
    "UserGroupReportTable",
    "UserGroupTable",
    "AuditEventSyncTable",
    "MigrationHistoryTable",
    "AuditEventTable",
    "ConnectionTable",
    "ReportTable",
    "UserTable",
    "data_db_metadata",
    "admin_db_metadata",
]
