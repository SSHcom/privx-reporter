"""Tests are not necessary for this module."""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Table, Text
from sqlalchemy.sql import func

# Table belongs to admin database
from lib.database.models.meta import admin_db_metadata

SessionTable = Table(
    "session",
    admin_db_metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, nullable=False),
    Column("user_id", Integer, ForeignKey("user.id"), nullable=False),
    # Hashed JWT token identifier (jti claim) - never store raw tokens
    Column("token_jti", String, nullable=False),
    Column("auth_source", String, nullable=False, server_default="local"),
    # OIDC session continuity fields. We want Reporter OIDC sessions to stay in sync with IdP after restore
    Column("oidc_access_token", Text, nullable=True),
    Column("oidc_refresh_token", Text, nullable=True),
    Column("oidc_id_token", Text, nullable=True),
    Column("oidc_access_expires_at", DateTime, nullable=True),
    Column("oidc_refresh_expires_at", DateTime, nullable=True),
    # Timestamps for session lifecycle (expiration via updated + UI_JWT_EXPIRATION_MINUTES env var)
    Column("created", DateTime, nullable=False, server_default=func.now()),
    Column("updated", DateTime, nullable=False, server_default=func.now(), onupdate=func.now()),
    # Optional tracking fields for security
    Column("ip_address", String, nullable=True),
    Column("user_agent", String, nullable=True),
)

# Index for quick session lookup by token jti
Index("idx_session_token_jti_unique", SessionTable.c.token_jti, unique=True)
# Index for finding all sessions for a user
Index("idx_session_user_id", SessionTable.c.user_id)
