"""Tests are not necessary for this module."""

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Table

# Table belongs to admin database
from lib.database.models.meta import admin_db_metadata

AltGroupTable = Table(
    "alt_group",
    admin_db_metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, nullable=False),
    Column("alt_group_view_id", Integer, ForeignKey("alt_group_view.id"), nullable=False),
    Column("group_name", String, nullable=False),
    Column("report_id", Integer, ForeignKey("report.id"), nullable=False),
    Column("sort_order", Integer, nullable=False, server_default="0"),
)

Index(
    "idx_alt_group_view_id_group_name_report_id_unique",
    AltGroupTable.c.alt_group_view_id,
    AltGroupTable.c.group_name,
    AltGroupTable.c.report_id,
    unique=True,
)

Index(
    "idx_alt_group_view_id_sort_order",
    AltGroupTable.c.alt_group_view_id,
    AltGroupTable.c.sort_order,
)
