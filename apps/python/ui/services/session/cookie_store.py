"""Cookie storage wrappers for the persisted UI session token.

Reading uses ``st.context.cookies`` (synchronous, from HTTP request headers)
so the session token is available on the very first script run after a full
page reload — no iframe round-trip required.

Writing and deleting still use the iframe-based ``CookieManager`` component
because ``st.context.cookies`` is read-only.
"""

from __future__ import annotations

import os

import streamlit as st
from streamlit.logger import get_logger

from ui.custom.cookie import CookieManager

SESSION_COOKIE_KEY = "ui_session_token"
_DEFAULT_COOKIE_MAX_AGE_MINUTES = 1440
_CM_KEY = "_session_cm"

logger = get_logger(__name__)


def init() -> None:
    """Create a CookieManager for write/delete operations on the current script run."""
    if _CM_KEY in st.session_state and isinstance(st.session_state[_CM_KEY], CookieManager):
        logger.debug("cookie_store.init: reusing existing CookieManager")
        return

    cm = CookieManager(key="session_cookie_mgr")
    st.session_state[_CM_KEY] = cm
    logger.debug("cookie_store.init: CookieManager created")


def get_session_token() -> str | None:
    """Read the session token from browser cookies via HTTP request headers.

    Uses ``st.context.cookies`` which is available synchronously on every
    script run, including the first run after a full page reload.
    """
    # st.context.cookies is a read-only dict parsed from the Cookie header.
    token = st.context.cookies.get(SESSION_COOKIE_KEY)
    if token is not None:
        logger.debug(
            "cookie_store.get_session_token: found token key=%s",
            SESSION_COOKIE_KEY,
        )
        logger.debug(
            "cookie_store.get_session_token: found token via st.context.cookies key=%s cookie_keys=%s",
            SESSION_COOKIE_KEY,
            sorted(st.context.cookies.keys()),
        )
        return str(token)

    logger.debug(
        "cookie_store.get_session_token: no token in st.context.cookies key=%s cookie_keys=%s",
        SESSION_COOKIE_KEY,
        sorted(st.context.cookies.keys()),
    )
    return None


def set_session_token(token: str) -> None:
    """Write a session token to browser cookies (iframe-based)."""
    logger.debug("cookie_store.set_session_token: setting cookie key=%s", SESSION_COOKIE_KEY)
    logger.debug(
        "cookie_store.set_session_token: setting cookie key=%s max_age_seconds=%s",
        SESSION_COOKIE_KEY,
        _cookie_max_age(),
    )
    _cm().set(
        SESSION_COOKIE_KEY,
        token,
        key="session_cookie_set",
        max_age=_cookie_max_age(),
        same_site="lax",
    )


def clear_session_token() -> None:
    """Delete the session token cookie (iframe-based)."""
    logger.info("cookie_store.clear_session_token: deleting cookie key=%s", SESSION_COOKIE_KEY)
    logger.debug("cookie_store.clear_session_token: deleting cookie key=%s", SESSION_COOKIE_KEY)
    _cm().delete(SESSION_COOKIE_KEY, key="session_cookie_delete")


def _cm() -> CookieManager:
    cm = st.session_state.get(_CM_KEY)
    if cm is None:
        raise RuntimeError("session cookie manager was not initialized before cookie access")
    return cm


def _cookie_max_age() -> float:
    raw = os.environ.get("UI_COOKIE_MAX_AGE_MINUTES", str(_DEFAULT_COOKIE_MAX_AGE_MINUTES))
    try:
        return float(max(1, int(raw)) * 60)
    except ValueError:
        return float(_DEFAULT_COOKIE_MAX_AGE_MINUTES * 60)
