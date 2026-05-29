"""Tests are not necessary for this module."""

from sqlalchemy import Column, Index, Integer, String, Table

# Table belongs to admin database
from lib.database.models.meta import admin_db_metadata

UserGroupTable = Table(
    "user_group",
    admin_db_metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, nullable=False),
    Column("name", String, nullable=False),
    Column("access_groups", String, nullable=True),
)

Index("idx_user_group_name_unique", UserGroupTable.c.name, unique=True)
