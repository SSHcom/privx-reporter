"""Password hashing and validation utilities using bcrypt."""

from __future__ import annotations

import bcrypt
import re

_SPECIAL_CHAR_RE = re.compile(r"[^A-Za-z0-9]")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: The plain text password to hash.

    Returns:
        The bcrypt hash as a string.
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def validate_password(password: str, hashed: str) -> bool:
    """Validate a password against a bcrypt hash.

    Args:
        password: The plain text password to validate.
        hashed: The bcrypt hash to check against.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except (ValueError, TypeError):
        # Non-bcrypt values (for example OIDC-only marker) are never valid local passwords.
        return False


def validate_password_policy(password: str) -> tuple[bool, str]:
    """Validate password strength policy.

    Policy:
    - at least 8 characters
    - at least one special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if _SPECIAL_CHAR_RE.search(password) is None:
        return False, "Password must contain at least one special character."
    return True, ""
