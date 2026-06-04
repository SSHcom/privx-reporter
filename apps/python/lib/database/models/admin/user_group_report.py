"""Tests are not necessary for this module."""

from sqlalchemy import Column, ForeignKey, Index, Integer, Table

# Table belongs to admin database
from lib.database.models.meta import admin_db_metadata

UserGroupReportTable = Table(
    "user_group_report",
    admin_db_metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, nullable=False),
    Column("user_group_id", Integer, ForeignKey("user_group.id"), nullable=False),
    Column("report_id", Integer, ForeignKey("report.id"), nullable=False),
)

Index(
    "idx_user_group_report_user_group_id_report_id_unique",
    UserGroupReportTable.c.user_group_id,
    UserGroupReportTable.c.report_id,
    unique=True,
)
