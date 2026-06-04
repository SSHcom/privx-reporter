"""Tests are not necessary for this module."""

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Table

# Table belongs to admin database
from lib.database.models.meta import admin_db_metadata

UserTable = Table(
    "user",
    admin_db_metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, nullable=False),
    Column("is_admin", Boolean, nullable=False, default=False),
    Column("has_profile", Boolean, nullable=False, default=True),
    Column("name", String, nullable=False),
    Column("display_name", String, nullable=False),
    Column("user_group_id", Integer, ForeignKey("user_group.id"), nullable=False),
    Column("encrypted_password", String, nullable=False),
)

Index("idx_user_name_unique", UserTable.c.name, unique=True)
