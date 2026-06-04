"""Tests are not necessary for this module."""

from sqlalchemy import Column, DateTime, Index, Integer, String, Table, func

from lib.database.models.meta import admin_db_metadata

MigrationHistoryTable = Table(
    "migration_history",
    admin_db_metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, nullable=False),
    Column("migration_name", String, nullable=False),
    Column("target_db", String, nullable=False),
    Column("applied_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

Index(
    "idx_migration_history_name_target_unique",
    MigrationHistoryTable.c.migration_name,
    MigrationHistoryTable.c.target_db,
    unique=True,
)
Index("idx_migration_history_applied_at", MigrationHistoryTable.c.applied_at)
