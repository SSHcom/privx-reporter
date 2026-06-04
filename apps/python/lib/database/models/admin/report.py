"""Tests are not necessary for this module."""

from sqlalchemy import Column, Index, Integer, String, Table

# Table belongs to admin database
from lib.database.models.meta import admin_db_metadata

ReportTable = Table(
    "report",
    admin_db_metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, nullable=False),
    Column("group_name", String, nullable=False),
    Column("report_name", String, nullable=False),
)

Index("idx_report_group_name_report_name_unique", ReportTable.c.group_name, ReportTable.c.report_name, unique=True)
