"""Tests are not necessary for this module."""

from sqlalchemy import Boolean, Column, Index, Integer, String, Table

# Table belongs to admin database
from lib.database.models.meta import admin_db_metadata

AuditEventSyncTable = Table(
    "audit_event_sync",
    admin_db_metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, nullable=False),
    Column("code", Integer, nullable=False),
    Column("enabled", Boolean, nullable=False),
    Column("name", String, nullable=False),
    Column("severity", String, nullable=False),
    Column("description", String, nullable=False),
)

Index("idx_audit_event_sync_code_unique", AuditEventSyncTable.c.code, unique=True)
