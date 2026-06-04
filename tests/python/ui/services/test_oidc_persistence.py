"""Tests for OIDC token persistence in session management.

This module verifies that OIDC tokens (access, refresh, and ID tokens) are
correctly persisted to the database and hydrated back into session state
during session creation and restoration flows.
"""

from __future__ import annotations

import datetime as dt
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ui.services.session import keys, session_manager


def _make_streamlit_stub() -> SimpleNamespace:
    """Create a minimal Streamlit stub for testing session state operations."""
    return SimpleNamespace(session_state={}, switch_page=MagicMock())


@pytest.mark.unit
def test_start_session_persists_oidc_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """OIDC login start should persist the oidc_access_token."""
    # Setup: Create stubs and mocks for Streamlit and session repository
    st_stub = _make_streamlit_stub()
    create_session = MagicMock(return_value=1)
    set_cookie = MagicMock()

    # Patch session manager dependencies
    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager.session_repo, "create_session", create_session)
    monkeypatch.setattr(session_manager, "_set_session_cookie", set_cookie)
    monkeypatch.setenv("UI_AUTH_MODE", "local,entra")

    # Execute: Start a new OIDC session with all required tokens
    now = dt.datetime.now(dt.UTC)
    token = session_manager.start_session(
        user_id=42,
        auth_source="oidc:entra",
        oidc_access_token="test-access-token",
        oidc_refresh_token="test-refresh-token",
        oidc_access_expires_at=now,
        oidc_refresh_expires_at=now,
        oidc_id_token="test-id-token",
        token_factory=lambda: "opaque-token",
    )

    # Verify: Session token is returned and all OIDC tokens are persisted
    assert token == "opaque-token"
    create_session.assert_called_once_with(
        user_id=42,
        token="opaque-token",
        auth_source="oidc:entra",
        oidc_access_token="test-access-token",
        oidc_refresh_token="test-refresh-token",
        oidc_access_expires_at=now,
        oidc_refresh_expires_at=now,
        oidc_id_token="test-id-token",
    )
    # Verify: OIDC access token is stored in session state for immediate use
    assert st_stub.session_state["oidc_access_token"] == "test-access-token"


@pytest.mark.unit
def test_restore_session_hydrates_oidc_access_token_with_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Restore should hydrate oidc_access_token from DB session and handle refresh if needed."""
    # Setup: Create Streamlit stub with unauthenticated state
    st_stub = _make_streamlit_stub()
    st_stub.session_state[keys.AUTHENTICATED] = False
    hydrate = MagicMock()

    # Patch session manager dependencies to return a valid session token
    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager, "get_session_token", lambda: "opaque-token")
    monkeypatch.setenv("UI_AUTH_MODE", "local,entra")

    # Setup: Configure token expiry 1 hour in the future to avoid triggering refresh
    now = dt.datetime.now(dt.UTC)
    expires_at = now + dt.timedelta(hours=1)

    # Mock session repository to return a valid OIDC session with all tokens
    monkeypatch.setattr(
        session_manager.session_repo,
        "get_session_by_token",
        lambda token: {
            "id": 7,
            "user_id": 99,
            "token_jti": token,
            "auth_source": "oidc:entra",
            "oidc_access_token": "persisted-access-token",
            "oidc_refresh_token": "persisted-refresh-token",
            "oidc_id_token": "persisted-id-token",
            "oidc_access_expires_at": expires_at,
            "oidc_refresh_expires_at": expires_at,
            "updated": now,
        },
    )
    monkeypatch.setattr(
        session_manager.session_repo, "get_latest_session_token_for_user", lambda _user_id: "opaque-token"
    )
    # Mock user lookup to return a valid user record
    monkeypatch.setattr(
        session_manager,
        "get_user",
        lambda user_id: {
            "id": user_id,
            "name": "alice",
            "display_name": "Alice",
            "group_name": "users",
            "has_profile": True,
        },
    )
    monkeypatch.setattr(session_manager, "hydrate_authenticated_state", hydrate)

    # Execute: Restore session from cookie/database
    restored = session_manager.restore_session()

    # Verify: Session is successfully restored
    assert restored is True
    # Verify: OIDC access token is hydrated into session state from database
    assert st_stub.session_state["oidc_access_token"] == "persisted-access-token"
    # Verify: Token expiry timestamp is correctly stored in session state
    assert st_stub.session_state["oidc_expires_at"] == expires_at.timestamp()
