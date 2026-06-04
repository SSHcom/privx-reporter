from __future__ import annotations

import os
from urllib.parse import urlencode

import requests
import streamlit as st


def _resolve_provider_name(auth_source: str | None) -> str | None:
    if not auth_source:
        return None
    if auth_source.startswith("oidc:"):
        provider = auth_source.split(":", 1)[1].strip()
        return provider or None
    return None


def _build_oidc_logout_url(*, provider_name: str) -> str | None:
    prefix = f"{provider_name.upper()}_"

    issuer = os.getenv(f"{prefix}OIDC_ISSUER", "").rstrip("/")
    client_id = os.getenv(f"{prefix}OIDC_CLIENT_ID", "")
    post_logout_redirect_uri = os.getenv(f"{prefix}OIDC_POST_LOGOUT_REDIRECT_URI", "")

    if not issuer or not client_id or not post_logout_redirect_uri:
        return None

    try:
        response = requests.get(
            f"{issuer}/.well-known/openid-configuration",
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
        "client_id": client_id,
        "post_logout_redirect_uri": post_logout_redirect_uri,
    }

    id_token_hint = st.session_state.get("oidc_id_token")
    if id_token_hint:
        params["id_token_hint"] = id_token_hint

    return f"{end_session_endpoint}?{urlencode(params)}"


def logout_user() -> None:
    from ui.services.session import session_manager
    from ui.services.session.state import clear_authenticated_state

    auth_source = st.session_state.get("auth_source")
    provider_name = _resolve_provider_name(auth_source)
    logout_url = _build_oidc_logout_url(provider_name=provider_name) if provider_name else None

    session_manager.end_session()

    clear_authenticated_state()

    st.session_state["auth_source"] = None
    st.session_state["oidc_id_token"] = None
    st.session_state["oidc_access_token"] = None
    st.session_state["oidc_refresh_token"] = None
    st.session_state["oidc_expires_at"] = None
    st.session_state["oidc_id_token_exp"] = None

    if logout_url:
        st.markdown(
            f'<meta http-equiv="refresh" content="0; url={logout_url}">',
            unsafe_allow_html=True,
        )
    else:
        st.switch_page("pages/_0_Login.py")
