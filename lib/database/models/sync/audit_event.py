"""Tests are not necessary for this module."""

from sqlalchemy import Column, DateTime, String, Table
from sqlalchemy.dialects.postgresql import JSONB

# Table belongs to data database
from lib.database.models.meta import data_db_metadata

AuditEventTable = Table(
    "audit_event",
    data_db_metadata,
    Column("timestamp", DateTime, primary_key=True, nullable=False),
    Column("record_id", String, primary_key=True, nullable=False),
    Column("event_id", String, nullable=True),
    Column("event_name", String, nullable=True),
    Column("data", JSONB, nullable=False),
)
