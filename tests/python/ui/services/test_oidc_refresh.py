from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ui.services.auth import oidc_refresh
from ui.services.session import keys


def _make_streamlit_stub() -> SimpleNamespace:
    """Create a mock Streamlit object with an empty session_state dictionary for testing."""
    return SimpleNamespace(session_state={})


def _setup_fake_session(st_stub: SimpleNamespace) -> None:
    """
    Set up a fake OIDC session in the given Streamlit stub.

    Simulates an authenticated OIDC session where the access token is already expired
    (expires_at is 10 seconds in the past), but the refresh token is still valid
    (refresh_expires_at is 3600 seconds in the future).
    """
    # Simulate an authenticated OIDC session where access token is already expired.
    st_stub.session_state.clear()
    st_stub.session_state["oidc_refresh_token"] = "fake-refresh-token"
    st_stub.session_state["oidc_access_token"] = "old-access-token"
    st_stub.session_state["oidc_id_token"] = "old-id-token"
    st_stub.session_state["oidc_expires_at"] = time.time() - 10
    st_stub.session_state["oidc_refresh_expires_at"] = time.time() + 3600
    st_stub.session_state["auth_source"] = "oidc:entra"
    st_stub.session_state[keys.SESSION_TOKEN] = "test-session-token"


@pytest.mark.unit
def test_refresh_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test successful OIDC token refresh flow.

    Verifies that when the IdP returns a valid token response, the system:
    - Updates all OIDC tokens in session state
    - Persists the new tokens to the database
    - Returns True to indicate success
    """
    st_stub = _make_streamlit_stub()
    _setup_fake_session(st_stub)

    # DB persistence succeeds in this happy-path case.
    update_oidc_session = MagicMock(return_value=True)

    # Mock HTTP response from IdP token endpoint with valid refresh token response.
    class FakeResponse:
        ok = True

        def json(self) -> dict[str, object]:
            # Minimal successful refresh payload from IdP token endpoint.
            return {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 3600,
                "refresh_expires_in": 7200,
                "id_token": "new-id-token",
            }

    # Mock all external dependencies: Streamlit state, OIDC config, HTTP requests, and DB operations.
    monkeypatch.setattr(oidc_refresh, "st", st_stub)
    monkeypatch.setattr(
        oidc_refresh,
        "_get_oidc_config",
        lambda provider_name=None: {
            "issuer": "http://issuer",
            "client_id": "client-id",
            "client_secret": "client-secret",
        },
    )
    monkeypatch.setattr(
        oidc_refresh,
        "_fetch_oidc_metadata",
        lambda issuer: {"token_endpoint": "http://fake/token", "jwks_uri": "http://fake/jwks"},
    )
    monkeypatch.setattr(oidc_refresh.requests, "post", lambda *args, **kwargs: FakeResponse())
    validate_refreshed_id_token = MagicMock(return_value={"sub": "subject-1"})
    monkeypatch.setattr(oidc_refresh, "_validate_refreshed_id_token", validate_refreshed_id_token)
    monkeypatch.setattr(oidc_refresh, "extract_id_token_exp", lambda token: 1234567890)
    monkeypatch.setattr("ui.db.session_repo.update_oidc_session", update_oidc_session)

    result = oidc_refresh._refresh_oidc_token()

    # Refresh should succeed and overwrite in-memory OIDC tokens.
    assert result is True
    assert st_stub.session_state["oidc_access_token"] == "new-access-token"
    assert st_stub.session_state["oidc_refresh_token"] == "new-refresh-token"
    assert st_stub.session_state["oidc_id_token"] == "new-id-token"
    assert st_stub.session_state["oidc_id_token_exp"] == 1234567890
    validate_refreshed_id_token.assert_called_once_with(
        new_id_token="new-id-token",
        existing_id_token="old-id-token",
        jwks_uri="http://fake/jwks",
        issuer="http://issuer",
        client_id="client-id",
    )
    # Refreshed tokens must also be persisted to the session row.
    update_oidc_session.assert_called_once()
    assert update_oidc_session.call_args.kwargs["token"] == "test-session-token"
    assert update_oidc_session.call_args.kwargs["oidc_access_token"] == "new-access-token"


@pytest.mark.unit
def test_refresh_missing_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test token refresh failure when access_token is missing from IdP response.

    Verifies that when the IdP returns a response without an access_token:
    - The refresh operation fails and returns False
    - Session state retains the old access token
    - No database updates are attempted
    """
    st_stub = _make_streamlit_stub()
    _setup_fake_session(st_stub)

    # Keep this mocked to ensure failure path does not write anything.
    update_oidc_session = MagicMock(return_value=True)

    # Mock HTTP response from IdP with malformed payload (missing required access_token field).
    class FakeResponse:
        ok = True

        def json(self) -> dict[str, object]:
            return {
                # Missing access_token should fail refresh.
                "expires_in": 3600,
            }

    # Mock all external dependencies: Streamlit state, OIDC config, HTTP requests, and DB operations.
    monkeypatch.setattr(oidc_refresh, "st", st_stub)
    monkeypatch.setattr(
        oidc_refresh,
        "_get_oidc_config",
        lambda provider_name=None: {
            "issuer": "http://issuer",
            "client_id": "client-id",
            "client_secret": "client-secret",
        },
    )
    monkeypatch.setattr(
        oidc_refresh,
        "_fetch_oidc_metadata",
        lambda issuer: {"token_endpoint": "http://fake/token"},
    )
    monkeypatch.setattr(oidc_refresh.requests, "post", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr("ui.db.session_repo.update_oidc_session", update_oidc_session)

    result = oidc_refresh._refresh_oidc_token()

    # Missing access token is a hard failure: keep prior state, skip DB writes.
    assert result is False
    assert st_stub.session_state["oidc_access_token"] == "old-access-token"
    update_oidc_session.assert_not_called()


@pytest.mark.unit
def test_refresh_rejects_unvalidated_new_id_token(monkeypatch: pytest.MonkeyPatch) -> None:
    st_stub = _make_streamlit_stub()
    _setup_fake_session(st_stub)
    update_oidc_session = MagicMock(return_value=True)

    class FakeResponse:
        ok = True

        def json(self) -> dict[str, object]:
            return {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 3600,
                "refresh_expires_in": 7200,
                "id_token": "subject-swapped-id-token",
            }

    monkeypatch.setattr(oidc_refresh, "st", st_stub)
    monkeypatch.setattr(
        oidc_refresh,
        "_get_oidc_config",
        lambda provider_name=None: {
            "issuer": "http://issuer",
            "client_id": "client-id",
            "client_secret": "client-secret",
        },
    )
    monkeypatch.setattr(
        oidc_refresh,
        "_fetch_oidc_metadata",
        lambda issuer: {"token_endpoint": "http://fake/token", "jwks_uri": "http://fake/jwks"},
    )
    monkeypatch.setattr(oidc_refresh.requests, "post", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(
        oidc_refresh,
        "_validate_refreshed_id_token",
        MagicMock(side_effect=ValueError("Refreshed ID token subject does not match existing session.")),
    )
    monkeypatch.setattr("ui.db.session_repo.update_oidc_session", update_oidc_session)

    result = oidc_refresh._refresh_oidc_token()

    assert result is False
    assert st_stub.session_state["oidc_access_token"] == "old-access-token"
    assert st_stub.session_state["oidc_refresh_token"] == "fake-refresh-token"
    assert st_stub.session_state["oidc_id_token"] == "old-id-token"
    update_oidc_session.assert_not_called()
