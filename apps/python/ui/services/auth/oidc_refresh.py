from __future__ import annotations

import os
from typing import Any

import jwt
import requests
import streamlit as st
from jwt import PyJWKClient
from streamlit.logger import get_logger

from ui.services.auth.oidc_claims import extract_id_token_exp

logger = get_logger(__name__)


def _preview(token: str | None) -> str:
    if not token:
        return "<none>"
    s = str(token)
    return s if len(s) <= 10 else f"{s[:6]}...{s[-4:]}"


def _response_error_summary(response: requests.Response) -> dict[str, object]:
    summary: dict[str, object] = {
        "status": response.status_code,
        "content_type": response.headers.get("content-type"),
    }
    try:
        payload = response.json()
    except ValueError:
        return summary

    if isinstance(payload, dict):
        summary["error"] = payload.get("error")
        summary["error_description"] = payload.get("error_description")
        summary["error_codes"] = payload.get("error_codes")
        summary["keys"] = sorted(payload.keys())
    return summary


def _get_oidc_config(provider_name: str) -> dict[str, str]:
    provider = str(provider_name or "").strip()
    if not provider:
        raise ValueError("Missing OIDC provider id")

    prefix = f"{provider.upper()}_"

    return {
        "issuer": os.environ[f"{prefix}OIDC_ISSUER"].rstrip("/"),
        "client_id": os.environ[f"{prefix}OIDC_CLIENT_ID"],
        "client_secret": os.environ[f"{prefix}OIDC_CLIENT_SECRET"],
    }


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_oidc_metadata(issuer: str) -> dict:
    response = requests.get(
        f"{issuer}/.well-known/openid-configuration",
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _unverified_id_token_sub(id_token: str | None) -> str | None:
    if not id_token:
        return None
    try:
        claims = jwt.decode(
            id_token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_aud": False,
                "verify_iss": False,
            },
        )
    except jwt.PyJWTError:
        return None
    sub = claims.get("sub") if isinstance(claims, dict) else None
    return str(sub) if sub else None


def _validate_refreshed_id_token(
    *,
    new_id_token: str,
    existing_id_token: str | None,
    jwks_uri: str,
    issuer: str,
    client_id: str,
) -> dict[str, Any]:
    existing_sub = _unverified_id_token_sub(existing_id_token)
    if not existing_sub:
        raise ValueError("Cannot validate refreshed ID token without existing session subject.")

    jwks_client = PyJWKClient(jwks_uri)
    signing_key = jwks_client.get_signing_key_from_jwt(new_id_token)
    claims: dict[str, Any] = jwt.decode(
        new_id_token,
        key=signing_key.key,
        algorithms=["RS256", "PS256", "ES256"],
        audience=client_id,
        issuer=issuer,
        options={"require": ["exp", "iat", "iss", "aud", "sub"]},
    )

    new_sub = str(claims.get("sub") or "")
    if new_sub != existing_sub:
        raise ValueError("Refreshed ID token subject does not match existing session.")
    return claims


def _refresh_oidc_token() -> bool:
    import datetime as dt
    import time

    from ui.db import session_repo
    from ui.services.session import keys

    refresh_token = st.session_state.get("oidc_refresh_token")
    session_token = st.session_state.get(keys.SESSION_TOKEN)

    if not refresh_token or not session_token:
        logger.debug(
            "OIDC refresh skipped missing refresh_token=%s session_token=%s",
            bool(refresh_token),
            bool(session_token),
        )
        return False

    current_exp = st.session_state.get("oidc_expires_at")
    seconds_left = None
    if isinstance(current_exp, (int, float)):
        seconds_left = max(0, int(current_exp - time.time()))

    logger.debug(
        "OIDC refresh trigger token_present=%s seconds_left=%s",
        bool(session_token),
        seconds_left,
    )

    try:
        auth_source = str(st.session_state.get("auth_source") or "")
        if not auth_source.startswith("oidc:"):
            return False
        provider_name = auth_source.split(":", 1)[1].strip()
        if not provider_name:
            return False

        cfg = _get_oidc_config(provider_name)
        metadata = _fetch_oidc_metadata(cfg["issuer"])

        response = requests.post(
            metadata["token_endpoint"],
            data={
                "grant_type": "refresh_token",
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "refresh_token": refresh_token,
            },
            timeout=10,
        )

        if not response.ok:
            logger.warning(
                "OIDC refresh failed token_present=%s error=%s",
                bool(session_token),
                _response_error_summary(response),
            )
            return False

        token_response = response.json()
        now = int(time.time())

        expires_in = int(token_response.get("expires_in", 0))
        refresh_expires_in = int(token_response.get("refresh_expires_in", 0))

        logger.debug(
            "OIDC refresh attempt token_present=%s expires_in=%s refresh_expires_in=%s",
            bool(session_token),
            expires_in,
            refresh_expires_in,
        )

        new_access_token = token_response.get("access_token")
        if not new_access_token:
            logger.error(
                "OIDC refresh response missing access_token token_present=%s keys=%s",
                bool(session_token),
                sorted(token_response.keys()),
            )
            return False

        new_refresh_token = token_response.get("refresh_token", refresh_token)
        existing_id_token = st.session_state.get("oidc_id_token")
        refreshed_id_token = token_response.get("id_token")
        if refreshed_id_token:
            _validate_refreshed_id_token(
                new_id_token=str(refreshed_id_token),
                existing_id_token=str(existing_id_token) if existing_id_token else None,
                jwks_uri=str(metadata["jwks_uri"]),
                issuer=cfg["issuer"],
                client_id=cfg["client_id"],
            )
        new_id_token = refreshed_id_token or existing_id_token

        oidc_expires_at_ts = now + expires_in if expires_in > 0 else None
        oidc_refresh_expires_at_ts = now + refresh_expires_in if refresh_expires_in > 0 else None

        st.session_state["oidc_access_token"] = new_access_token
        st.session_state["oidc_refresh_token"] = new_refresh_token
        st.session_state["oidc_id_token"] = new_id_token
        st.session_state["oidc_expires_at"] = oidc_expires_at_ts
        st.session_state["oidc_refresh_expires_at"] = oidc_refresh_expires_at_ts
        st.session_state["oidc_id_token_exp"] = extract_id_token_exp(str(new_id_token) if new_id_token else None)

        oidc_access_expires_at = (
            dt.datetime.fromtimestamp(oidc_expires_at_ts, tz=dt.UTC) if oidc_expires_at_ts is not None else None
        )
        oidc_refresh_expires_at = (
            dt.datetime.fromtimestamp(oidc_refresh_expires_at_ts, tz=dt.UTC)
            if oidc_refresh_expires_at_ts is not None
            else None
        )

        updated = session_repo.update_oidc_session(
            token=str(session_token),
            oidc_access_token=str(new_access_token) if new_access_token else None,
            oidc_refresh_token=new_refresh_token,
            oidc_access_expires_at=oidc_access_expires_at,
            oidc_refresh_expires_at=oidc_refresh_expires_at,
            oidc_id_token=str(new_id_token) if new_id_token else None,
        )
        if not updated:
            logger.error(
                "OIDC refresh succeeded but DB session update failed token_present=%s",
                bool(session_token),
            )
            return False

        logger.info(
            "OIDC refresh success token_present=%s access_expires_in=%s refresh_expires_in=%s",
            bool(session_token),
            expires_in,
            refresh_expires_in,
        )
        return True

    except Exception:
        logger.debug("OIDC refresh exception token=%s", _preview(str(session_token)), exc_info=True)
        return False
