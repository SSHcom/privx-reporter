"""Session orchestration for cookie, DB session, and Streamlit auth state."""

from __future__ import annotations

import datetime as dt
import hashlib
import os
from typing import TYPE_CHECKING

import streamlit as st
from streamlit.logger import get_logger

from ui.db import session_repo
from ui.db.user_queries import get_user
from ui.services.auth.oidc_claims import extract_id_token_exp
from ui.services.auth.oidc_refresh import _refresh_oidc_token
from ui.services.session import cookie_store, keys, lifecycle
from ui.services.session.state import clear_authenticated_state, hydrate_authenticated_state

SESSION_COOKIE_KEY = cookie_store.SESSION_COOKIE_KEY
_CM_KEY = cookie_store._CM_KEY
_COOKIE_SYNC_DEADLINE_KEY = "_session_cookie_sync_deadline"
_COOKIE_SYNC_GRACE_SECONDS = 15
_LAST_RESTORE_LOG_KEY = "_session_last_restore_log_key"

logger = get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable


def _preview(token: str | None) -> str:
    if not token:
        return "<none>"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]
    return f"<sha256:{digest}>"


def _allowed_auth_sources() -> set[str]:
    raw = os.getenv("UI_AUTH_MODE", "local").strip().lower()
    modes = {mode.strip() for mode in raw.split(",") if mode.strip()}
    if not modes:
        modes = {"local"}

    allowed = {"local"} if "local" in modes else set()
    allowed.update(f"oidc:{provider}" for provider in modes if provider not in {"local", "oidc"})
    return allowed


def _is_allowed_auth_source(auth_source: str) -> bool:
    return auth_source in _allowed_auth_sources()


def _validate_session_auth_payload(
    *,
    auth_source: str,
    oidc_access_token: str | None,
    oidc_refresh_token: str | None,
    oidc_access_expires_at: dt.datetime | None,
    oidc_refresh_expires_at: dt.datetime | None,
    oidc_id_token: str | None,
) -> None:
    if auth_source == "local":
        if any(
            value is not None
            for value in (
                oidc_access_token,
                oidc_refresh_token,
                oidc_access_expires_at,
                oidc_refresh_expires_at,
                oidc_id_token,
            )
        ):
            raise ValueError("Local sessions must not include OIDC tokens or expiries")
        return

    if auth_source.startswith("oidc:"):
        if not oidc_access_token:
            raise ValueError("OIDC sessions require oidc_access_token")
        if not oidc_refresh_token:
            raise ValueError("OIDC sessions require oidc_refresh_token")
        if oidc_access_expires_at is None:
            raise ValueError("OIDC sessions require oidc_access_expires_at")


def init() -> None:
    """Initialize cookie storage for this script run."""
    cookie_store.init()


def get_session_token() -> str | None:
    """Read the current session token from browser cookies."""
    token = cookie_store.get_session_token()
    logger.debug("get_session_token -> present=%s", bool(token))
    return token


def restore_session() -> bool:
    """Restore app authentication state from persisted cookie and DB session.

    Session restore has two layers:
    1. Reporter session: browser cookie + DB-backed session row
    2. OIDC session: refresh/id/access token validity for IdP-authenticated users

    A valid Reporter DB session alone is not sufficient for OIDC users. If the
    upstream OIDC refresh flow fails, the Reporter session is ended as well.
    """
    cookie_token = get_session_token()
    in_memory_token = st.session_state.get(keys.SESSION_TOKEN)
    grace_active = _cookie_sync_grace_active()
    memory_token = str(in_memory_token) if in_memory_token else None

    logger.info(
        "restore_session: start has_cookie_token=%s has_memory_token=%s authenticated=%s grace_active=%s",
        bool(cookie_token),
        bool(memory_token),
        st.session_state.get(keys.AUTHENTICATED, False),
        grace_active,
    )

    # Decide which Reporter session token to trust for this run.
    #
    # st.context.cookies can lag behind cookie writes for a short time after
    # login/logout. During that window, prefer the in-memory token and keep
    # retrying cookie synchronization.
    if memory_token and cookie_token and cookie_token != memory_token:
        token = memory_token
        logger.warning(
            "restore_session: token_source=in_memory reason=cookie_mismatch has_cookie_token=%s has_memory_token=%s",
            bool(cookie_token),
            bool(memory_token),
        )
        _sync_cookie_once(token)
        st.session_state[_COOKIE_SYNC_DEADLINE_KEY] = dt.datetime.now(dt.UTC) + dt.timedelta(
            seconds=_COOKIE_SYNC_GRACE_SECONDS
        )
    elif memory_token and not cookie_token:
        token = memory_token
        logger.debug("restore_session: token_source=in_memory reason=missing_cookie token=%s", _preview(token))
        _sync_cookie_once(token)
        st.session_state[_COOKIE_SYNC_DEADLINE_KEY] = dt.datetime.now(dt.UTC) + dt.timedelta(
            seconds=_COOKIE_SYNC_GRACE_SECONDS
        )
    elif grace_active and memory_token:
        token = memory_token
        logger.debug("restore_session: token_source=in_memory reason=cookie_sync_grace token=%s", _preview(token))
        if cookie_token and cookie_token != token:
            logger.debug(
                "restore_session: ignoring stale cookie during grace has_cookie_token=%s has_memory_token=%s",
                bool(cookie_token),
                bool(token),
            )
    elif cookie_token:
        token = cookie_token
        st.session_state.pop(_COOKIE_SYNC_DEADLINE_KEY, None)
        # logger.info("restore_session: token_source=cookie token=%s", _preview(token))
    else:
        st.session_state.pop(_COOKIE_SYNC_DEADLINE_KEY, None)
        if st.session_state.get(keys.AUTHENTICATED, False) and not memory_token:
            logger.warning("restore_session: authenticated_state_without_token -> clearing state")
            clear_authenticated_state()
        logger.info("restore_session: no token available")
        return False

    # Load the persisted Reporter session row.
    session = session_repo.get_session_by_token(token)
    if session is None:
        logger.warning(
            "restore_session: no DB session for has_token=%s has_cookie_token=%s has_memory_token=%s grace_active=%s "
            "cm_initialized=%s",
            bool(token),
            bool(cookie_token),
            bool(memory_token),
            grace_active,
            _CM_KEY in st.session_state,
        )
        cookie_store.clear_session_token()
        logger.debug("restore_session: requested_cookie_delete token=%s", _preview(token))
        clear_authenticated_state()
        return False

    # Enforce single active session per user by accepting only the most recent
    # login token. Older browser sessions are invalidated on restore.
    latest_user_token = session_repo.get_latest_session_token_for_user(int(session["user_id"]))
    if latest_user_token and latest_user_token != token:
        logger.info(
            "restore_session: superseded_session user_id=%s",
            session["user_id"],
        )
        _end_specific_session(token)
        return False

    updated_at = lifecycle.ensure_utc(session.get("updated"))
    if updated_at is None:
        logger.debug("restore_session: invalid updated timestamp token=%s", _preview(token))
        _end_specific_session(token)
        return False

    remaining_ttl = lifecycle.session_ttl_remaining(updated_at)
    ttl_seconds = int(remaining_ttl.total_seconds())

    if lifecycle.is_session_expired(remaining_ttl):
        logger.debug("restore_session: reporter_session_expired token=%s ttl=%s", _preview(token), ttl_seconds)
        _end_specific_session(token)
        return False

    # Restore persisted auth source first so subsequent logic knows which auth
    # model applies to this session.
    auth_source = str(session.get("auth_source", "local"))
    if auth_source == "oidc":
        # Legacy, unprefixed provider mode is deprecated. Fail closed: require an explicit provider id
        # (auth_source must be "oidc:<provider>").
        logger.debug("restore_session: deprecated_auth_source=oidc -> ending session token=%s", _preview(token))
        _end_specific_session(token)
        return False
    if not _is_allowed_auth_source(auth_source):
        logger.warning("restore_session: disallowed_auth_source=%s -> ending session", auth_source)
        _end_specific_session(token)
        return False
    st.session_state["auth_source"] = auth_source

    oidc_access_seconds_left: int | None = None
    oidc_refresh_seconds_left: int | None = None

    if auth_source.startswith("oidc:"):
        # Restore persisted OIDC material from the DB-backed session.
        #
        # Reporter DB session validity does not override IdP token validity.
        # For OIDC users, the session remains usable only while refresh logic
        # can maintain an active upstream token set.
        access_expires_at = lifecycle.ensure_utc(session.get("oidc_access_expires_at"))
        refresh_expires_at = lifecycle.ensure_utc(session.get("oidc_refresh_expires_at"))

        st.session_state["oidc_access_token"] = session.get("oidc_access_token")
        st.session_state["oidc_refresh_token"] = session.get("oidc_refresh_token")
        st.session_state["oidc_id_token"] = session.get("oidc_id_token")
        st.session_state["oidc_expires_at"] = access_expires_at.timestamp() if access_expires_at else None
        st.session_state["oidc_refresh_expires_at"] = refresh_expires_at.timestamp() if refresh_expires_at else None
        st.session_state["oidc_id_token_exp"] = extract_id_token_exp(session.get("oidc_id_token"))

        now_ts = dt.datetime.now(dt.UTC).timestamp()
        expires_at = st.session_state.get("oidc_expires_at")
        refresh_at = st.session_state.get("oidc_refresh_expires_at")

        if isinstance(expires_at, (int, float)):
            oidc_access_seconds_left = max(0, int(expires_at - now_ts))
        if isinstance(refresh_at, (int, float)):
            oidc_refresh_seconds_left = max(0, int(refresh_at - now_ts))
    else:
        # Ensure no stale OIDC values leak into a locally-authenticated session.
        st.session_state.pop("oidc_access_token", None)
        st.session_state.pop("oidc_refresh_token", None)
        st.session_state.pop("oidc_id_token", None)
        st.session_state.pop("oidc_expires_at", None)
        st.session_state.pop("oidc_refresh_expires_at", None)
        st.session_state.pop("oidc_id_token_exp", None)

    logger.debug(
        "restore_session: loaded auth_source=%s reporter_ttl=%s oidc_access_ttl=%s oidc_refresh_ttl=%s",
        auth_source,
        ttl_seconds,
        oidc_access_seconds_left,
        oidc_refresh_seconds_left,
    )

    if auth_source.startswith("oidc:") and oidc_access_seconds_left is None:
        logger.warning(
            "restore_session: oidc_access_expiry_missing refresh_ttl=%s -> ending session",
            oidc_refresh_seconds_left,
        )
        _end_specific_session(token)
        return False

    if auth_source.startswith("oidc:") and oidc_refresh_seconds_left is not None and oidc_refresh_seconds_left <= 0:
        logger.warning(
            "restore_session: oidc_refresh_unavailable access_ttl=%s refresh_ttl=%s -> ending session",
            oidc_access_seconds_left,
            oidc_refresh_seconds_left,
        )
        _end_specific_session(token)
        return False

    # Refresh OIDC access token shortly before expiry.
    #
    # If refresh fails, the Reporter session is also ended. This prevents a
    # locally-restored UI session from outliving the upstream IdP session.
    if auth_source.startswith("oidc:") and oidc_access_seconds_left is not None and oidc_access_seconds_left < 10:
        logger.info(
            "restore_session: oidc_access_near_expiry access_ttl=%s refresh_ttl=%s -> refreshing",
            oidc_access_seconds_left,
            oidc_refresh_seconds_left,
        )
        if _refresh_oidc_token():
            logger.debug("restore_session: oidc_refresh_succeeded token=%s", _preview(token))

            # Ensure access token actually exists
            if not st.session_state.get("oidc_access_token"):
                logger.error("OIDC refresh produced no access token")
                _end_specific_session(token)
                return False

            # Reload DB session (avoid stale session object)
            session = session_repo.get_session_by_token(token)
            if session is None:
                logger.error("restore_session: session missing after refresh")
                _end_specific_session(token)
                return False

        else:
            logger.warning(
                "restore_session: oidc_refresh_failed access_ttl=%s refresh_ttl=%s -> ending session",
                oidc_access_seconds_left,
                oidc_refresh_seconds_left,
            )
            _end_specific_session(token)
            return False

    # Extend the Reporter session activity window if needed.
    if lifecycle.should_extend_session(remaining_ttl):
        if session_repo.touch_session(token):
            logger.debug(
                "restore_session: extended_reporter_session remaining=%s",
                remaining_ttl,
            )
        else:
            logger.debug("restore_session: failed_to_extend_reporter_session token=%s", _preview(token))

    user = get_user(int(session["user_id"]))
    if user is None:
        logger.warning(
            "restore_session: user_not_found user_id=%s -> ending session",
            session["user_id"],
        )
        session_repo.end_session(token)
        clear_authenticated_state()
        return False

    hydrate_authenticated_state(user)
    st.session_state[keys.SESSION_TOKEN] = token
    st.session_state["auth_source"] = auth_source

    logger.info(
        "restore_session: success user_id=%s auth_source=%s",
        user["id"],
        auth_source,
    )
    _log_restore_success(user_id=user["id"], username=user["name"], token=token)
    return True


def _cookie_sync_grace_active() -> bool:
    deadline = st.session_state.get(_COOKIE_SYNC_DEADLINE_KEY)
    return isinstance(deadline, dt.datetime) and deadline > dt.datetime.now(dt.UTC)


def _sync_cookie_once(token: str) -> None:
    # Component writes are async; only stop retrying once request cookies reflect the token.
    current_cookie_token = cookie_store.get_session_token()
    if current_cookie_token == token:
        return

    cookie_store.set_session_token(token)


def _end_specific_session(token: str) -> None:
    """End a specific DB session and clean up cookie/state.

    Unlike ``end_session()`` this targets the exact *token* passed in,
    avoiding the risk of accidentally killing a different valid session
    that may already be stored in ``session_state``.
    """
    session_repo.end_session(token)
    cookie_store.clear_session_token()
    clear_authenticated_state()


def _set_session_cookie(token: str) -> None:
    """Persist session token in browser cookie storage."""
    # Callback/login code paths may call start_session() before page bootstrap
    # initialized CookieManager. Ensure cookie writes are self-sufficient.
    cookie_store.init()
    _sync_cookie_once(token)


def start_session(
    *,
    user_id: int,
    auth_source: str = "local",
    oidc_access_token: str | None = None,
    oidc_refresh_token: str | None = None,
    oidc_access_expires_at: dt.datetime | None = None,
    oidc_refresh_expires_at: dt.datetime | None = None,
    oidc_id_token: str | None = None,
    token_factory: Callable[[], str] | None = None,
) -> str:
    """Create and persist a new session for a user."""
    if not _is_allowed_auth_source(auth_source):
        raise ValueError(f"Unsupported auth_source: {auth_source}")
    _validate_session_auth_payload(
        auth_source=auth_source,
        oidc_access_token=oidc_access_token,
        oidc_refresh_token=oidc_refresh_token,
        oidc_access_expires_at=oidc_access_expires_at,
        oidc_refresh_expires_at=oidc_refresh_expires_at,
        oidc_id_token=oidc_id_token,
    )

    if token_factory is None:
        import secrets

        token_factory = lambda: secrets.token_urlsafe(32)  # noqa: E731

    token = token_factory()
    session_id = session_repo.create_session(
        user_id=user_id,
        token=token,
        auth_source=auth_source,
        oidc_access_token=oidc_access_token,
        oidc_refresh_token=oidc_refresh_token,
        oidc_access_expires_at=oidc_access_expires_at,
        oidc_refresh_expires_at=oidc_refresh_expires_at,
        oidc_id_token=oidc_id_token,
    )
    logger.info(
        "start_session user_id=%s session_id=%s auth_source=%s token_present=%s",
        user_id,
        session_id,
        auth_source,
        bool(token),
    )

    _set_session_cookie(token)
    st.session_state[_COOKIE_SYNC_DEADLINE_KEY] = dt.datetime.now(dt.UTC) + dt.timedelta(
        seconds=_COOKIE_SYNC_GRACE_SECONDS
    )
    st.session_state[keys.SESSION_TOKEN] = token
    st.session_state["auth_source"] = auth_source

    if auth_source.startswith("oidc:"):
        st.session_state["oidc_access_token"] = oidc_access_token
        st.session_state["oidc_refresh_token"] = oidc_refresh_token
        st.session_state["oidc_id_token"] = oidc_id_token
        st.session_state["oidc_refresh_expires_at"] = oidc_refresh_expires_at
        st.session_state["oidc_expires_at"] = oidc_access_expires_at.timestamp() if oidc_access_expires_at else None

    return token


def end_session(*, redirect: bool = False) -> None:
    """End DB session, clear cookie token, and wipe authenticated state."""
    token = st.session_state.get(keys.SESSION_TOKEN) or get_session_token()
    context = getattr(st, "context", None)
    cookies = getattr(context, "cookies", {}) if context is not None else {}
    cookie_keys = sorted(cookies.keys()) if hasattr(cookies, "keys") else []
    if token:
        logger.debug("end_session token=%s", _preview(token))
        session_repo.end_session(str(token))
    else:
        logger.debug("end_session - no token found")

    logger.debug(
        "end_session: clearing cookie/state token_present=%s cm_initialized=%s cookie_keys=%s",
        bool(token),
        _CM_KEY in st.session_state,
        cookie_keys,
    )
    cookie_store.clear_session_token()
    st.session_state.pop(_COOKIE_SYNC_DEADLINE_KEY, None)
    st.session_state.pop(_LAST_RESTORE_LOG_KEY, None)
    st.session_state.pop("oidc_access_token", None)
    st.session_state.pop("oidc_refresh_token", None)
    st.session_state.pop("oidc_id_token", None)
    st.session_state.pop("oidc_expires_at", None)
    st.session_state.pop("oidc_id_token_exp", None)
    st.session_state.pop("oidc_refresh_expires_at", None)
    clear_authenticated_state()

    if redirect:
        st.switch_page("pages/_0_Login.py")


def _log_restore_success(*, user_id: int, username: str, token: str) -> None:
    log_key = f"{user_id}:{_preview(token)}"
    if st.session_state.get(_LAST_RESTORE_LOG_KEY) == log_key:
        logger.debug(
            "restore_session: restored (duplicate) user_id=%s username=%s",
            user_id,
            username,
        )
        return

    st.session_state[_LAST_RESTORE_LOG_KEY] = log_key
    logger.info(
        "restore_session: restored user_id=%s username=%s",
        user_id,
        username,
    )
