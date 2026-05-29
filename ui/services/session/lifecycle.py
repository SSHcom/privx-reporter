"""Session lifecycle calculations for expiry and extension windows."""

from __future__ import annotations

import datetime as dt
import os

_DEFAULT_JWT_EXPIRATION_MINUTES = 60
_SESSION_EXTENSION_WINDOW_MINUTES = 10


def session_ttl_remaining(updated_at: dt.datetime) -> dt.timedelta:
    """Return remaining session TTL based on the last activity timestamp."""
    now_utc = dt.datetime.now(dt.UTC)
    ttl = dt.timedelta(minutes=_jwt_expiration_minutes())
    return (updated_at + ttl) - now_utc


def should_extend_session(remaining_ttl: dt.timedelta) -> bool:
    """Return True when session activity should refresh updated timestamp."""
    return remaining_ttl <= dt.timedelta(minutes=_SESSION_EXTENSION_WINDOW_MINUTES)


def is_session_expired(remaining_ttl: dt.timedelta) -> bool:
    """Return True when session TTL has elapsed."""
    return remaining_ttl <= dt.timedelta(0)


def _jwt_expiration_minutes() -> int:
    """Read UI JWT expiration in minutes from environment."""
    raw = os.environ.get("UI_JWT_EXPIRATION_MINUTES", str(_DEFAULT_JWT_EXPIRATION_MINUTES))
    try:
        return max(1, int(raw))
    except ValueError:
        return _DEFAULT_JWT_EXPIRATION_MINUTES


def ensure_utc(value: object) -> dt.datetime | None:
    """Normalize datetime values to UTC, preserving instant semantics."""
    if not isinstance(value, dt.datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.UTC)
    return value.astimezone(dt.UTC)
