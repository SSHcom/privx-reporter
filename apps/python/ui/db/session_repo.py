"""Database access helpers for persisted UI sessions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, insert, inspect, select, text, update
from sqlalchemy.sql import func

from lib.clients.postgresql import use_database
from lib.database.models.admin.session import SessionTable

if TYPE_CHECKING:
    from datetime import datetime


_SESSION_SCHEMA_VERIFIED = False


def _ensure_session_schema() -> None:
    """Backfill session columns required by newer auth/session flows."""
    global _SESSION_SCHEMA_VERIFIED
    if _SESSION_SCHEMA_VERIFIED:
        return

    db = use_database("admin")
    inspector = inspect(db.engine)
    existing_columns = {column["name"] for column in inspector.get_columns("session")}

    ddl_statements: list[str] = []
    if "auth_source" not in existing_columns:
        ddl_statements.append(
            "ALTER TABLE session ADD COLUMN IF NOT EXISTS auth_source VARCHAR NOT NULL DEFAULT 'local'"
        )
    if "oidc_refresh_token" not in existing_columns:
        ddl_statements.append("ALTER TABLE session ADD COLUMN IF NOT EXISTS oidc_refresh_token TEXT")
    if "oidc_access_token" not in existing_columns:
        ddl_statements.append("ALTER TABLE session ADD COLUMN IF NOT EXISTS oidc_access_token TEXT")
    if "oidc_id_token" not in existing_columns:
        ddl_statements.append("ALTER TABLE session ADD COLUMN IF NOT EXISTS oidc_id_token TEXT")
    if "oidc_access_expires_at" not in existing_columns:
        ddl_statements.append("ALTER TABLE session ADD COLUMN IF NOT EXISTS oidc_access_expires_at TIMESTAMP")
    if "oidc_refresh_expires_at" not in existing_columns:
        ddl_statements.append("ALTER TABLE session ADD COLUMN IF NOT EXISTS oidc_refresh_expires_at TIMESTAMP")

    if ddl_statements:
        for statement in ddl_statements:
            db.connection.execute(text(statement))
        db.connection.commit()

    _SESSION_SCHEMA_VERIFIED = True


def create_session(
    *,
    user_id: int,
    token: str,
    auth_source: str = "local",
    oidc_access_token: str | None = None,
    oidc_refresh_token: str | None = None,
    oidc_access_expires_at: datetime | None = None,
    oidc_refresh_expires_at: datetime | None = None,
    oidc_id_token: str | None = None,
) -> int | None:
    """Create a new persisted session row and return its ID."""
    _ensure_session_schema()
    db = use_database("admin")

    result = db.connection.execute(
        insert(SessionTable).returning(SessionTable.c.id),
        {
            "user_id": user_id,
            "token_jti": token,
            "auth_source": auth_source,
            "oidc_access_token": oidc_access_token,
            "oidc_refresh_token": oidc_refresh_token,
            "oidc_access_expires_at": oidc_access_expires_at,
            "oidc_refresh_expires_at": oidc_refresh_expires_at,
            "oidc_id_token": oidc_id_token,
        },
    )
    row = result.fetchone()
    db.connection.commit()
    return int(row[0]) if row else None


def get_session_by_token(token: str) -> dict[str, Any] | None:
    _ensure_session_schema()
    db = use_database("admin")

    try:
        result = db.connection.execute(
            select(
                SessionTable.c.id,
                SessionTable.c.user_id,
                SessionTable.c.token_jti,
                SessionTable.c.auth_source,
                SessionTable.c.oidc_access_token,
                SessionTable.c.oidc_refresh_token,
                SessionTable.c.oidc_access_expires_at,
                SessionTable.c.oidc_refresh_expires_at,
                SessionTable.c.oidc_id_token,
                SessionTable.c.created,
                SessionTable.c.updated,
            ).where(SessionTable.c.token_jti == token)
        )
        row = result.fetchone()
        if row is None:
            return None
        return dict(zip(result.keys(), row))
    finally:
        # SELECT starts an implicit transaction on the cached connection.
        # Close it explicitly so follow-up begin() calls can succeed.
        if db.connection.in_transaction():
            db.connection.rollback()


def get_latest_session_token_for_user(user_id: int) -> str | None:
    """Return latest Reporter session token for a given user."""
    _ensure_session_schema()
    db = use_database("admin")

    try:
        result = db.connection.execute(
            select(SessionTable.c.token_jti)
            .where(SessionTable.c.user_id == user_id)
            .order_by(SessionTable.c.created.desc(), SessionTable.c.id.desc())
            .limit(1)
        )
        row = result.fetchone()
        return str(row[0]) if row and row[0] is not None else None
    finally:
        if db.connection.in_transaction():
            db.connection.rollback()


def end_session(token: str) -> bool:
    """Delete a persisted session by token identifier."""
    _ensure_session_schema()
    db = use_database("admin")

    result = db.connection.execute(delete(SessionTable).where(SessionTable.c.token_jti == token))
    db.connection.commit()
    return bool(result.rowcount and result.rowcount > 0)


def update_oidc_session(
    *,
    token: str,
    oidc_access_token: str | None,
    oidc_refresh_token: str | None,
    oidc_access_expires_at: datetime | None,
    oidc_refresh_expires_at: datetime | None,
    oidc_id_token: str | None,
) -> bool:
    """Update persisted OIDC token metadata for an existing session."""
    _ensure_session_schema()
    db = use_database("admin")

    result = db.connection.execute(
        update(SessionTable)
        .where(SessionTable.c.token_jti == token)
        .values(
            oidc_access_token=oidc_access_token,
            oidc_refresh_token=oidc_refresh_token,
            oidc_access_expires_at=oidc_access_expires_at,
            oidc_refresh_expires_at=oidc_refresh_expires_at,
            oidc_id_token=oidc_id_token,
            updated=func.now(),
        )
    )
    db.connection.commit()
    return bool(result.rowcount and result.rowcount > 0)


def touch_session(token: str) -> bool:
    """Refresh the persisted session activity timestamp."""
    _ensure_session_schema()
    db = use_database("admin")

    result = db.connection.execute(
        update(SessionTable).where(SessionTable.c.token_jti == token).values(updated=func.now())
    )
    db.connection.commit()
    return bool(result.rowcount and result.rowcount > 0)
