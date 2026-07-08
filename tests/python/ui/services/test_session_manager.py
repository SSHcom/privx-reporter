from __future__ import annotations

import datetime as dt
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ui.services.session import keys, session_manager


def _make_streamlit_stub() -> SimpleNamespace:
    return SimpleNamespace(session_state={}, switch_page=MagicMock())


def _latest_session_token_for_user(_user_id: int) -> str:
    return "opaque-token"


@pytest.mark.unit
def test_start_session_creates_persisted_session_and_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    """Successful login start should persist a session and write cookie."""
    st_stub = _make_streamlit_stub()
    create_session = MagicMock(return_value=1)
    set_cookie = MagicMock()

    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager.session_repo, "create_session", create_session)
    monkeypatch.setattr(session_manager, "_set_session_cookie", set_cookie)

    token = session_manager.start_session(user_id=42, token_factory=lambda: "opaque-token")

    assert token == "opaque-token"
    create_session.assert_called_once_with(
        user_id=42,
        token="opaque-token",
        auth_source="local",
        oidc_access_token=None,
        oidc_refresh_token=None,
        oidc_access_expires_at=None,
        oidc_refresh_expires_at=None,
        oidc_id_token=None,
    )
    set_cookie.assert_called_once_with("opaque-token")
    assert st_stub.session_state[keys.SESSION_TOKEN] == "opaque-token"
    assert st_stub.session_state["auth_source"] == "local"


@pytest.mark.unit
def test_start_session_initializes_cookie_store_without_page_init(monkeypatch: pytest.MonkeyPatch) -> None:
    """start_session must be self-sufficient for callback paths."""
    st_stub = _make_streamlit_stub()
    create_session = MagicMock(return_value=1)
    init_cookie_store = MagicMock()
    set_cookie = MagicMock()

    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager.session_repo, "create_session", create_session)
    monkeypatch.setattr(session_manager.cookie_store, "init", init_cookie_store)
    monkeypatch.setattr(session_manager.cookie_store, "get_session_token", lambda: None)
    monkeypatch.setattr(session_manager.cookie_store, "set_session_token", set_cookie)

    token = session_manager.start_session(user_id=42, token_factory=lambda: "opaque-token")

    assert token == "opaque-token"
    create_session.assert_called_once()
    init_cookie_store.assert_called_once_with()
    set_cookie.assert_called_once_with("opaque-token")
    assert st_stub.session_state[keys.SESSION_TOKEN] == "opaque-token"


@pytest.mark.unit
def test_start_session_rejects_local_auth_source_with_oidc_material(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local sessions must not persist OIDC token state."""
    st_stub = _make_streamlit_stub()
    create_session = MagicMock()
    set_cookie = MagicMock()

    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager.session_repo, "create_session", create_session)
    monkeypatch.setattr(session_manager, "_set_session_cookie", set_cookie)

    with pytest.raises(ValueError, match="Local sessions must not include OIDC tokens or expiries"):
        session_manager.start_session(
            user_id=42,
            auth_source="local",
            oidc_refresh_token="refresh-token",
            token_factory=lambda: "opaque-token",
        )

    create_session.assert_not_called()
    set_cookie.assert_not_called()


@pytest.mark.unit
def test_start_session_rejects_auth_source_not_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Session start should reject auth sources for disabled OIDC providers."""
    st_stub = _make_streamlit_stub()
    create_session = MagicMock()
    set_cookie = MagicMock()

    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager.session_repo, "create_session", create_session)
    monkeypatch.setattr(session_manager, "_set_session_cookie", set_cookie)
    monkeypatch.setenv("OIDC_2_ENABLED", "true")

    with pytest.raises(ValueError, match="Unsupported auth_source: oidc:1"):
        session_manager.start_session(user_id=42, auth_source="oidc:1", token_factory=lambda: "opaque-token")

    create_session.assert_not_called()
    set_cookie.assert_not_called()


@pytest.mark.unit
def test_start_session_rejects_oidc_auth_source_without_required_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OIDC sessions must include access token, refresh token, and expiries."""
    st_stub = _make_streamlit_stub()
    create_session = MagicMock()
    set_cookie = MagicMock()

    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager.session_repo, "create_session", create_session)
    monkeypatch.setattr(session_manager, "_set_session_cookie", set_cookie)
    monkeypatch.setenv("OIDC_2_ENABLED", "true")

    with pytest.raises(ValueError, match="OIDC sessions require oidc_refresh_token"):
        session_manager.start_session(
            user_id=42,
            auth_source="oidc:2",
            oidc_access_token="access-token",
            oidc_access_expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(seconds=300),
            oidc_refresh_expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(seconds=600),
            token_factory=lambda: "opaque-token",
        )

    create_session.assert_not_called()
    set_cookie.assert_not_called()


@pytest.mark.unit
def test_start_session_accepts_consistent_oidc_auth_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """OIDC session start should persist when required token state is complete."""
    st_stub = _make_streamlit_stub()
    create_session = MagicMock(return_value=1)
    set_cookie = MagicMock()
    access_expires_at = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=300)
    refresh_expires_at = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=600)

    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager.session_repo, "create_session", create_session)
    monkeypatch.setattr(session_manager, "_set_session_cookie", set_cookie)
    monkeypatch.setenv("OIDC_2_ENABLED", "true")

    token = session_manager.start_session(
        user_id=42,
        auth_source="oidc:2",
        oidc_access_token="access-token",
        oidc_refresh_token="refresh-token",
        oidc_access_expires_at=access_expires_at,
        oidc_refresh_expires_at=refresh_expires_at,
        oidc_id_token="id-token",
        token_factory=lambda: "opaque-token",
    )

    assert token == "opaque-token"
    create_session.assert_called_once_with(
        user_id=42,
        token="opaque-token",
        auth_source="oidc:2",
        oidc_access_token="access-token",
        oidc_refresh_token="refresh-token",
        oidc_access_expires_at=access_expires_at,
        oidc_refresh_expires_at=refresh_expires_at,
        oidc_id_token="id-token",
    )
    set_cookie.assert_called_once_with("opaque-token")


@pytest.mark.unit
def test_restore_session_hydrates_authenticated_state_from_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refresh restore should hydrate state when cookie and DB session are valid."""
    st_stub = _make_streamlit_stub()
    st_stub.session_state[keys.AUTHENTICATED] = False
    hydrate = MagicMock()

    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager, "get_session_token", lambda: "opaque-token")
    monkeypatch.setenv("OIDC_2_ENABLED", "true")
    monkeypatch.setattr(
        session_manager.session_repo,
        "get_session_by_token",
        lambda token: {
            "id": 7,
            "user_id": 99,
            "token_jti": token,
            "updated": dt.datetime.now(dt.UTC),
        },
    )
    monkeypatch.setattr(
        session_manager.session_repo,
        "get_latest_session_token_for_user",
        _latest_session_token_for_user,
    )
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

    restored = session_manager.restore_session()

    assert restored is True
    hydrate.assert_called_once()
    assert st_stub.session_state[keys.SESSION_TOKEN] == "opaque-token"


@pytest.mark.unit
def test_restore_session_invalid_cookie_fails_closed_and_clears_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid cookie token should not authenticate and should trigger cleanup."""
    st_stub = _make_streamlit_stub()
    st_stub.session_state[keys.AUTHENTICATED] = False
    clear_cookie = MagicMock()
    clear_state = MagicMock()

    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager, "get_session_token", lambda: "missing-token")
    monkeypatch.setattr(session_manager.session_repo, "get_session_by_token", lambda _: None)
    monkeypatch.setattr(session_manager.cookie_store, "clear_session_token", clear_cookie)
    monkeypatch.setattr(session_manager, "clear_authenticated_state", clear_state)

    restored = session_manager.restore_session()

    assert restored is False
    clear_cookie.assert_called_once()
    clear_state.assert_called_once()


@pytest.mark.unit
def test_restore_session_uses_in_memory_token_during_cookie_sync_grace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing cookie right after login should use in-memory token briefly."""
    st_stub = _make_streamlit_stub()
    st_stub.session_state[keys.AUTHENTICATED] = True
    st_stub.session_state[keys.SESSION_TOKEN] = "opaque-token"
    st_stub.session_state["_session_cookie_sync_deadline"] = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=10)
    hydrate = MagicMock()
    refresh_cookie = MagicMock()

    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager, "get_session_token", lambda: None)
    monkeypatch.setattr(
        session_manager.session_repo,
        "get_session_by_token",
        lambda token: {
            "id": 7,
            "user_id": 99,
            "token_jti": token,
            "updated": dt.datetime.now(dt.UTC),
        },
    )
    monkeypatch.setattr(
        session_manager.session_repo,
        "get_latest_session_token_for_user",
        _latest_session_token_for_user,
    )
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
    monkeypatch.setattr(session_manager.cookie_store, "set_session_token", refresh_cookie)

    restored = session_manager.restore_session()

    assert restored is True
    hydrate.assert_called_once()
    refresh_cookie.assert_called_once_with("opaque-token")


@pytest.mark.unit
def test_restore_session_uses_in_memory_token_when_cookie_missing_after_grace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cookie-missing state should not force relogin when in-memory token exists."""
    st_stub = _make_streamlit_stub()
    st_stub.session_state[keys.AUTHENTICATED] = True
    st_stub.session_state[keys.SESSION_TOKEN] = "opaque-token"
    hydrate = MagicMock()
    refresh_cookie = MagicMock()

    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager, "get_session_token", lambda: None)
    monkeypatch.setattr(
        session_manager.session_repo,
        "get_session_by_token",
        lambda token: {
            "id": 7,
            "user_id": 99,
            "token_jti": token,
            "updated": dt.datetime.now(dt.UTC),
        },
    )
    monkeypatch.setattr(
        session_manager.session_repo,
        "get_latest_session_token_for_user",
        _latest_session_token_for_user,
    )
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
    monkeypatch.setattr(session_manager.cookie_store, "set_session_token", refresh_cookie)

    restored = session_manager.restore_session()

    assert restored is True
    hydrate.assert_called_once()
    refresh_cookie.assert_called_once_with("opaque-token")
    assert st_stub.session_state[keys.SESSION_TOKEN] == "opaque-token"


@pytest.mark.unit
def test_restore_session_prefers_in_memory_token_when_cookie_mismatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When cookie and memory disagree, in-memory token should win and refresh cookie."""
    st_stub = _make_streamlit_stub()
    st_stub.session_state[keys.AUTHENTICATED] = True
    st_stub.session_state[keys.SESSION_TOKEN] = "new-token"
    hydrate = MagicMock()
    refresh_cookie = MagicMock()

    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager, "get_session_token", lambda: "stale-cookie-token")
    monkeypatch.setattr(
        session_manager.session_repo,
        "get_session_by_token",
        lambda token: {
            "id": 7,
            "user_id": 99,
            "token_jti": token,
            "updated": dt.datetime.now(dt.UTC),
        },
    )
    monkeypatch.setattr(session_manager.session_repo, "get_latest_session_token_for_user", lambda _user_id: "new-token")
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
    monkeypatch.setattr(session_manager.cookie_store, "set_session_token", refresh_cookie)

    restored = session_manager.restore_session()

    assert restored is True
    hydrate.assert_called_once()
    refresh_cookie.assert_called_once_with("new-token")
    assert st_stub.session_state[keys.SESSION_TOKEN] == "new-token"


@pytest.mark.unit
def test_restore_session_ends_session_for_auth_source_not_in_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Restore should fail closed when DB session auth_source is not enabled in config."""
    st_stub = _make_streamlit_stub()
    end_specific_session = MagicMock()
    hydrate = MagicMock()

    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager, "get_session_token", lambda: "opaque-token")
    monkeypatch.setenv("OIDC_2_ENABLED", "true")
    monkeypatch.setattr(
        session_manager.session_repo,
        "get_session_by_token",
        lambda token: {
            "id": 7,
            "user_id": 99,
            "token_jti": token,
            "auth_source": "oidc:1",
            "updated": dt.datetime.now(dt.UTC),
        },
    )
    monkeypatch.setattr(
        session_manager.session_repo,
        "get_latest_session_token_for_user",
        _latest_session_token_for_user,
    )
    monkeypatch.setattr(session_manager, "_end_specific_session", end_specific_session)
    monkeypatch.setattr(session_manager, "hydrate_authenticated_state", hydrate)

    restored = session_manager.restore_session()

    assert restored is False
    end_specific_session.assert_called_once_with("opaque-token")
    hydrate.assert_not_called()


@pytest.mark.unit
def test_restore_session_allows_oidc_session_when_refresh_expiry_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OIDC session restore should allow providers that omit refresh expiry metadata."""
    st_stub = _make_streamlit_stub()
    hydrate = MagicMock()
    refresh_oidc_token = MagicMock()

    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager, "get_session_token", lambda: "opaque-token")
    monkeypatch.setenv("OIDC_2_ENABLED", "true")
    monkeypatch.setattr(
        session_manager.session_repo,
        "get_session_by_token",
        lambda token: {
            "id": 7,
            "user_id": 99,
            "token_jti": token,
            "auth_source": "oidc:2",
            "oidc_access_token": "access-token",
            "oidc_refresh_token": "refresh-token",
            "oidc_id_token": "id-token",
            "oidc_access_expires_at": dt.datetime.now(dt.UTC) + dt.timedelta(seconds=300),
            "oidc_refresh_expires_at": None,
            "updated": dt.datetime.now(dt.UTC),
        },
    )
    monkeypatch.setattr(
        session_manager.session_repo,
        "get_latest_session_token_for_user",
        _latest_session_token_for_user,
    )
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
    monkeypatch.setattr(session_manager, "_refresh_oidc_token", refresh_oidc_token)
    monkeypatch.setattr(session_manager, "extract_id_token_exp", lambda _id_token: None)

    restored = session_manager.restore_session()

    assert restored is True
    hydrate.assert_called_once()
    refresh_oidc_token.assert_not_called()


@pytest.mark.unit
def test_restore_session_ends_oidc_session_when_access_expiry_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OIDC session restore should fail closed when access expiry is unavailable."""
    st_stub = _make_streamlit_stub()
    end_specific_session = MagicMock()
    refresh_oidc_token = MagicMock()

    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager, "get_session_token", lambda: "opaque-token")
    monkeypatch.setattr(
        session_manager.session_repo,
        "get_session_by_token",
        lambda token: {
            "id": 7,
            "user_id": 99,
            "token_jti": token,
            "auth_source": "oidc:entra",
            "oidc_access_token": "access-token",
            "oidc_refresh_token": "refresh-token",
            "oidc_id_token": "id-token",
            "oidc_access_expires_at": None,
            "oidc_refresh_expires_at": dt.datetime.now(dt.UTC) + dt.timedelta(seconds=300),
            "updated": dt.datetime.now(dt.UTC),
        },
    )
    monkeypatch.setattr(
        session_manager.session_repo,
        "get_latest_session_token_for_user",
        _latest_session_token_for_user,
    )
    monkeypatch.setattr(session_manager, "_end_specific_session", end_specific_session)
    monkeypatch.setattr(session_manager, "_refresh_oidc_token", refresh_oidc_token)
    monkeypatch.setattr(session_manager, "extract_id_token_exp", lambda _id_token: None)

    restored = session_manager.restore_session()

    assert restored is False
    end_specific_session.assert_called_once_with("opaque-token")
    refresh_oidc_token.assert_not_called()


@pytest.mark.unit
def test_restore_session_ends_oidc_session_when_refresh_token_expired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OIDC session restore should fail closed when refresh token is already expired."""
    st_stub = _make_streamlit_stub()
    end_specific_session = MagicMock()
    refresh_oidc_token = MagicMock()

    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager, "get_session_token", lambda: "opaque-token")
    monkeypatch.setattr(
        session_manager.session_repo,
        "get_session_by_token",
        lambda token: {
            "id": 7,
            "user_id": 99,
            "token_jti": token,
            "auth_source": "oidc:entra",
            "oidc_access_token": "access-token",
            "oidc_refresh_token": "refresh-token",
            "oidc_id_token": "id-token",
            "oidc_access_expires_at": dt.datetime.now(dt.UTC) + dt.timedelta(seconds=5),
            "oidc_refresh_expires_at": dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1),
            "updated": dt.datetime.now(dt.UTC),
        },
    )
    monkeypatch.setattr(
        session_manager.session_repo,
        "get_latest_session_token_for_user",
        _latest_session_token_for_user,
    )
    monkeypatch.setattr(session_manager, "_end_specific_session", end_specific_session)
    monkeypatch.setattr(session_manager, "_refresh_oidc_token", refresh_oidc_token)
    monkeypatch.setattr(session_manager, "extract_id_token_exp", lambda _id_token: None)

    restored = session_manager.restore_session()

    assert restored is False
    end_specific_session.assert_called_once_with("opaque-token")
    refresh_oidc_token.assert_not_called()


@pytest.mark.unit
def test_set_session_cookie_initializes_cookie_store(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cookie write helper should initialize CookieManager before writing."""
    init_cookie_store = MagicMock()
    set_cookie = MagicMock()
    monkeypatch.setattr(session_manager.cookie_store, "init", init_cookie_store)
    monkeypatch.setattr(session_manager.cookie_store, "set_session_token", set_cookie)
    monkeypatch.setattr(session_manager.cookie_store, "get_session_token", lambda: None)

    session_manager._set_session_cookie("opaque-token")

    init_cookie_store.assert_called_once_with()
    set_cookie.assert_called_once_with("opaque-token")


@pytest.mark.unit
def test_end_session_clears_db_cookie_and_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Logout should clear persisted session and redirect to login."""
    st_stub = _make_streamlit_stub()
    st_stub.session_state[keys.SESSION_TOKEN] = "opaque-token"
    end_repo_session = MagicMock(return_value=True)
    clear_cookie = MagicMock()
    clear_state = MagicMock()

    monkeypatch.setattr(session_manager, "st", st_stub)
    monkeypatch.setattr(session_manager.session_repo, "end_session", end_repo_session)
    monkeypatch.setattr(session_manager.cookie_store, "clear_session_token", clear_cookie)
    monkeypatch.setattr(session_manager, "clear_authenticated_state", clear_state)

    session_manager.end_session(redirect=True)

    end_repo_session.assert_called_once_with("opaque-token")
    clear_cookie.assert_called_once()
    clear_state.assert_called_once()
    st_stub.switch_page.assert_called_once_with("pages/_0_Login.py")
