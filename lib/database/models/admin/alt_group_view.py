"""Tests are not necessary for this module."""

from sqlalchemy import Column, Index, Integer, String, Table

# Table belongs to admin database
from lib.database.models.meta import admin_db_metadata

AltGroupViewTable = Table(
    "alt_group_view",
    admin_db_metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, nullable=False),
    Column("name", String, nullable=False),
)

Index("idx_alt_group_view_name_unique", AltGroupViewTable.c.name, unique=True)
