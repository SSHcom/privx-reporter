"""Streamlit session-state initialization and auth-state helpers."""

from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlencode

import requests
import streamlit as st

from ui.services.permissions import UserPermissions, can_edit_profile, is_admin, is_superadmin_username
from ui.services.session import keys as keys
from ui.services.user_service import get_privx_user_ids


def init_session_state() -> None:
    """Initialize session-state variables used by the UI."""
    if keys.AUTHENTICATED not in st.session_state:
        st.session_state[keys.AUTHENTICATED] = False

    if keys.USERNAME not in st.session_state:
        st.session_state[keys.USERNAME] = None

    if keys.DISPLAY_NAME not in st.session_state:
        st.session_state[keys.DISPLAY_NAME] = None

    if keys.USER_ID not in st.session_state:
        st.session_state[keys.USER_ID] = None

    if keys.USER_GROUP_ID not in st.session_state:
        st.session_state[keys.USER_GROUP_ID] = None

    if keys.HAS_PROFILE not in st.session_state:
        st.session_state[keys.HAS_PROFILE] = None

    if keys.USER_GROUP not in st.session_state:
        st.session_state[keys.USER_GROUP] = None

    if keys.USER_PERMISSIONS not in st.session_state:
        st.session_state[keys.USER_PERMISSIONS] = None

    if keys.VIEWABLE_REPORTS not in st.session_state:
        st.session_state[keys.VIEWABLE_REPORTS] = None

    if keys.RESOLVED_REPORT_VIEWS not in st.session_state:
        st.session_state[keys.RESOLVED_REPORT_VIEWS] = None

    if keys.SELECTED_PRIMARY not in st.session_state:
        st.session_state[keys.SELECTED_PRIMARY] = None

    if keys.SELECTED_SUBCOMMAND not in st.session_state:
        st.session_state[keys.SELECTED_SUBCOMMAND] = None

    if keys.SELECTED_ALT_GROUP_VIEW not in st.session_state:
        st.session_state[keys.SELECTED_ALT_GROUP_VIEW] = None

    if keys.DASHBOARD_VIEW not in st.session_state:
        st.session_state[keys.DASHBOARD_VIEW] = "overview"

    if keys.SESSION_TOKEN not in st.session_state:
        st.session_state[keys.SESSION_TOKEN] = None

    if keys.PRIVX_USER_ID not in st.session_state:
        st.session_state[keys.PRIVX_USER_ID] = None

    if keys.PRIVX_USER_IDS not in st.session_state:
        st.session_state[keys.PRIVX_USER_IDS] = []

    if keys.PRIVX_USER_MATCHES not in st.session_state:
        st.session_state[keys.PRIVX_USER_MATCHES] = []

    if keys.PRIVX_USER_LOOKUP_USERNAME not in st.session_state:
        st.session_state[keys.PRIVX_USER_LOOKUP_USERNAME] = None

    if keys.PRIVX_USER_LOOKUP_DONE not in st.session_state:
        st.session_state[keys.PRIVX_USER_LOOKUP_DONE] = False


def require_auth() -> None:
    """Redirect to login when the user is not authenticated."""
    if not st.session_state.get(keys.AUTHENTICATED, False):
        st.switch_page("pages/_0_Login.py")


def hydrate_authenticated_state(user_row: dict[str, Any]) -> None:
    """Populate authenticated session state from a database user row."""
    prior_username = st.session_state.get(keys.USERNAME)
    prior_group = st.session_state.get(keys.USER_GROUP)
    should_reset_report_cache = prior_username != user_row["name"] or prior_group != user_row["group_name"]
    should_reset_privx_lookup_cache = prior_username != user_row["name"]

    permissions = UserPermissions(
        group=user_row["group_name"],
        display_name=user_row["display_name"],
    )
    st.session_state[keys.AUTHENTICATED] = True
    st.session_state[keys.USERNAME] = user_row["name"]
    st.session_state[keys.DISPLAY_NAME] = permissions.display_name
    st.session_state[keys.USER_PERMISSIONS] = permissions
    st.session_state[keys.USER_ID] = user_row["id"]
    st.session_state[keys.USER_GROUP_ID] = user_row["user_group_id"]
    st.session_state[keys.HAS_PROFILE] = user_row["has_profile"]
    st.session_state[keys.USER_GROUP] = user_row["group_name"]

    if should_reset_report_cache:
        st.session_state[keys.VIEWABLE_REPORTS] = None
        st.session_state[keys.RESOLVED_REPORT_VIEWS] = None

    if should_reset_privx_lookup_cache:
        st.session_state[keys.PRIVX_USER_ID] = None
        st.session_state[keys.PRIVX_USER_IDS] = []
        st.session_state[keys.PRIVX_USER_MATCHES] = []
        st.session_state[keys.PRIVX_USER_LOOKUP_USERNAME] = None
        st.session_state[keys.PRIVX_USER_LOOKUP_DONE] = False

    # Resolve local-authenticated UI user to matching PrivX users once per username.
    # Page/view permission checks rely on this cached session state.
    if str(st.session_state.get("auth_source") or "").strip().lower() == "local":
        username = str(st.session_state.get(keys.USERNAME) or "").strip()
        if username:
            get_privx_user_ids(username)

    # if st.session_state.get(keys.RESOLVED_REPORT_VIEWS) is None:
    #    from ui.services import report_view_resolver

    # report_view_resolver.prime_report_view_cache()


def oidc_session_is_expired(skew_seconds: int = 5) -> bool:
    expires_at = st.session_state.get("oidc_expires_at")
    id_token_exp = st.session_state.get("oidc_id_token_exp")
    now_ts = int(time.time())

    if isinstance(expires_at, int) and now_ts >= expires_at - skew_seconds:
        return True

    if isinstance(id_token_exp, int) and now_ts >= id_token_exp - skew_seconds:
        return True

    return False


def enforce_oidc_session_freshness() -> None:
    auth_source = st.session_state.get("auth_source")
    is_authenticated = st.session_state.get(keys.AUTHENTICATED, False)

    if not is_authenticated or auth_source != "oidc":
        return

    if not oidc_session_is_expired():
        return

    clear_authenticated_state()
    st.session_state["auth_source"] = None
    st.session_state["oidc_id_token"] = None
    st.session_state["oidc_access_token"] = None
    st.session_state["oidc_refresh_token"] = None
    st.session_state["oidc_expires_at"] = None
    st.session_state["oidc_id_token_exp"] = None

    st.warning("Your sign-in session expired. Please log in again.")
    st.switch_page("pages/_0_Login.py")


def build_oidc_logout_url() -> str | None:
    try:
        cfg = {
            "issuer": os.environ["OIDC_ISSUER"].rstrip("/"),
            "client_id": os.environ["OIDC_CLIENT_ID"],
            "post_logout_redirect_uri": os.environ["OIDC_POST_LOGOUT_REDIRECT_URI"],
        }
    except Exception:
        return None

    post_logout_redirect_uri = cfg.get("post_logout_redirect_uri")

    if not post_logout_redirect_uri:
        return None

    try:
        response = requests.get(
            f"{cfg['issuer']}/.well-known/openid-configuration",
            timeout=10,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        metadata = response.json()
    except Exception:
        return None

    end_session_endpoint = str(metadata.get("end_session_endpoint") or "").strip()
    if not end_session_endpoint:
        return None

    params = {
        "client_id": cfg["client_id"],
        "post_logout_redirect_uri": post_logout_redirect_uri,
    }
    id_token_hint = st.session_state.get("oidc_id_token")
    if id_token_hint:
        params["id_token_hint"] = str(id_token_hint)

    return f"{end_session_endpoint}?{urlencode(params)}"


def clear_authenticated_state() -> None:
    """Clear authenticated session-state values."""
    st.session_state[keys.AUTHENTICATED] = False
    st.session_state[keys.USERNAME] = None
    st.session_state[keys.DISPLAY_NAME] = None
    st.session_state[keys.USER_ID] = None
    st.session_state[keys.USER_GROUP_ID] = None
    st.session_state[keys.HAS_PROFILE] = None
    st.session_state[keys.USER_GROUP] = None
    st.session_state[keys.USER_PERMISSIONS] = None
    st.session_state[keys.VIEWABLE_REPORTS] = None
    st.session_state[keys.RESOLVED_REPORT_VIEWS] = None
    st.session_state[keys.SELECTED_PRIMARY] = None
    st.session_state[keys.SELECTED_SUBCOMMAND] = None
    st.session_state[keys.SELECTED_ALT_GROUP_VIEW] = None
    st.session_state[keys.SESSION_TOKEN] = None
    st.session_state[keys.PRIVX_USER_ID] = None
    st.session_state[keys.PRIVX_USER_IDS] = []
    st.session_state[keys.PRIVX_USER_MATCHES] = []
    st.session_state[keys.PRIVX_USER_LOOKUP_USERNAME] = None
    st.session_state[keys.PRIVX_USER_LOOKUP_DONE] = False


__all__ = [
    "can_edit_profile",
    "clear_authenticated_state",
    "hydrate_authenticated_state",
    "init_session_state",
    "is_admin",
    "is_superadmin_username",
    "require_auth",
    "enforce_oidc_session_freshness",
]
