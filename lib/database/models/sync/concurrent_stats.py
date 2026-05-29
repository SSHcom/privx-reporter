"""Tests are not necessary for this module."""

from sqlalchemy import Column, DateTime, Table
from sqlalchemy.dialects.postgresql import JSONB

# Table belongs to data database
from lib.database.models.meta import data_db_metadata

ConcurrentStatsTable = Table(
    "concurrent_stats",
    data_db_metadata,
    Column("timestamp", DateTime, primary_key=True, nullable=False),
    Column("data", JSONB, nullable=False),
)
