"""Tests are not necessary for this module."""

from sqlalchemy import Column, DateTime, Index, String, Table, Text
from sqlalchemy.sql import func

from lib.database.models.meta import admin_db_metadata

AppConfigTable = Table(
    "app_config",
    admin_db_metadata,
    Column("setting_key", String, nullable=False),
    Column("value", Text, nullable=False, server_default=""),
    Column("updated", DateTime, nullable=False, server_default=func.now(), onupdate=func.now()),
)

Index("idx_app_config_key_unique", AppConfigTable.c.setting_key, unique=True)
