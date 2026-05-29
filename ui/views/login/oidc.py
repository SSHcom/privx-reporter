"""OIDC login/callback flow for the Streamlit login page.

This module owns:
1. Building the IdP authorization URL and redirect parameters.
2. Handling callback code exchange and ID-token validation.
3. Bridging validated IdP identity to a local Reporter user.
4. Writing authenticated OIDC state into Streamlit session state.
"""

from __future__ import annotations

import html
import json
import secrets
import time
from datetime import UTC, datetime
from urllib.parse import urlencode

import jwt
import requests
import streamlit as st
from jwt import PyJWKClient
from streamlit.logger import get_logger
from ui.db.user_queries import create_oidc_user, get_user_for_login
from ui.services.session import keys, session_manager
from ui.services.session.state import hydrate_authenticated_state
from ui.views.login import oidc_callback, oidc_config, oidc_crypto, oidc_groups

OIDC_LAST_CODE_KEY = "oidc_last_code"
OIDC_PENDING_TOKEN_RESPONSE_KEY = "oidc_pending_token_response"
OIDC_PENDING_CLAIMS_KEY = "oidc_pending_claims"
OIDC_PENDING_USERNAME_KEY = "oidc_pending_username"
OIDC_ID_TOKEN_KEY = "oidc_id_token"
OIDC_ACCESS_TOKEN_KEY = "oidc_access_token"
OIDC_REFRESH_TOKEN_KEY = "oidc_refresh_token"
OIDC_EXPIRES_AT_KEY = "oidc_expires_at"
OIDC_REFRESH_EXPIRES_AT_KEY = "oidc_refresh_expires_at"
OIDC_ID_TOKEN_EXP_KEY = "oidc_id_token_exp"
OIDC_GROUP_CLAIM_PATH_KEY = "oidc_group_claim_path"
OIDC_GROUP_CLAIM_VALUES_KEY = "oidc_group_claim_values"
OIDC_GROUP_MAPPING_MATCH_KEY = "oidc_group_mapping_match"

log = get_logger(__name__)


def _log_flow_step(step: int, message: str, *args: object, branch: str | None = None) -> None:
    """Emit linear OIDC flow steps with optional branch suffixes (A/B/C)."""
    branch_suffix = branch.strip().upper() if branch else ""
    log.info(f"OIDC FLOW STEP %02d{branch_suffix}: " + message, step, *args)


def _preview(value: object | None) -> str:
    """Return a short, log-safe preview for potentially sensitive values."""
    if value is None:
        return "<none>"
    s = str(value)
    return s if len(s) <= 10 else f"{s[:6]}...{s[-4:]}"


def _claims_summary(claims: dict) -> dict[str, object]:
    """Return a minimal claim subset for logs; avoid dumping full PII claims."""
    return {
        "has_sub": bool(claims.get("sub")),
        "has_preferred_username": bool(claims.get("preferred_username")),
        "has_email": bool(claims.get("email")),
        "iss": claims.get("iss"),
        "aud": claims.get("aud"),
        "exp": claims.get("exp"),
        "has_nonce": bool(claims.get("nonce")),
        "tid": claims.get("tid"),
        "oid": claims.get("oid"),
        "roles_count": len(claims.get("roles", []) or []),
        "groups_count": len(claims.get("groups", []) or []),
    }


def _token_response_summary(token_response: dict) -> dict[str, object]:
    """Return a minimal token-response summary for logs."""
    return {
        "keys": sorted(token_response.keys()),
        "token_type": token_response.get("token_type"),
        "scope": token_response.get("scope"),
        "expires_in": token_response.get("expires_in"),
        "refresh_expires_in": token_response.get("refresh_expires_in"),
        "has_access_token": bool(token_response.get("access_token")),
        "has_refresh_token": bool(token_response.get("refresh_token")),
        "has_id_token": bool(token_response.get("id_token")),
    }


def _session_state_oidc_summary() -> dict[str, object]:
    """Return a safe summary of OIDC/session state for logs."""
    return {
        "authenticated": st.session_state.get(keys.AUTHENTICATED, False),
        "auth_source": st.session_state.get("auth_source"),
        "has_session_token": bool(st.session_state.get(keys.SESSION_TOKEN)),
        "has_oidc_id_token": bool(st.session_state.get(OIDC_ID_TOKEN_KEY)),
        "has_oidc_access_token": bool(st.session_state.get(OIDC_ACCESS_TOKEN_KEY)),
        "has_oidc_refresh_token": bool(st.session_state.get(OIDC_REFRESH_TOKEN_KEY)),
        "oidc_expires_at": st.session_state.get(OIDC_EXPIRES_AT_KEY),
        "oidc_refresh_expires_at": st.session_state.get(OIDC_REFRESH_EXPIRES_AT_KEY),
        "oidc_id_token_exp": st.session_state.get(OIDC_ID_TOKEN_EXP_KEY),
        "has_last_code": bool(st.session_state.get(OIDC_LAST_CODE_KEY)),
        "has_pending_token_response": st.session_state.get(OIDC_PENDING_TOKEN_RESPONSE_KEY) is not None,
        "has_pending_claims": st.session_state.get(OIDC_PENDING_CLAIMS_KEY) is not None,
        "has_pending_username": st.session_state.get(OIDC_PENDING_USERNAME_KEY) is not None,
    }


def _response_error_summary(response: requests.Response) -> dict[str, object]:
    """Return a minimal error summary without logging raw response bodies."""
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
    return oidc_config.get_oidc_config(provider_name)


def _get_provider_display_name(provider_name: str) -> str:
    return oidc_config.get_provider_display_name(provider_name)


def _get_provider_icon_svg(provider_name: str) -> str | None:
    return oidc_config.get_provider_icon_svg(provider_name)


def _env_flag(name: str, default: bool = False) -> bool:
    return oidc_config.env_flag(name, default)


def _auto_provision_enabled() -> bool:
    return oidc_config.auto_provision_enabled()


def _auto_provision_require_email() -> bool:
    return oidc_config.auto_provision_require_email()


def _allowed_email_domains() -> set[str]:
    return oidc_config.allowed_email_domains()


def _is_email_allowed(email: str) -> bool:
    return oidc_config.is_email_allowed(email)


def _group_claim_name() -> str:
    return oidc_groups.group_claim_name()


def _group_mapping() -> dict[str, str]:
    return oidc_groups.group_mapping()


def _claim_values(claims: dict, claim_path: str) -> list[str]:
    return oidc_groups.claim_values(claims, claim_path)


def _resolve_group_by_ref(group_ref: str) -> tuple[int, str] | None:
    return oidc_groups.resolve_group_by_ref(group_ref)


def _resolve_mapped_user_group(provider_name: str, claims: dict) -> tuple[int, str] | None:
    claim_name = _group_claim_name()
    mapping = _group_mapping()
    values = _claim_values(claims, claim_name)
    log.info(
        "OIDC group mapping probe provider=%s claim=%s claim_values=%s mapping_keys=%s",
        provider_name,
        claim_name,
        values,
        sorted(mapping.keys()),
    )
    if not mapping:
        log.info("OIDC group mapping disabled: OIDC_GROUP_MAPPING not set")
        return None
    if not values:
        log.info("OIDC group mapping: no claim values found for claim=%s", claim_name)
        return None
    mapping_ci = {k.lower(): v for k, v in mapping.items()}
    # Precedence is claim-order based: first matching IdP group wins.
    for source_group in values:
        target_ref = mapping.get(source_group) or mapping_ci.get(source_group.lower())
        if not target_ref:
            continue
        resolved = _resolve_group_by_ref(str(target_ref))
        if resolved is None:
            log.warning(
                "OIDC group mapping matched source=%s but target group ref=%s was not found",
                source_group,
                target_ref,
            )
            continue
        log.info(
            "OIDC group mapping resolved source=%s -> target=%s(%s)",
            source_group,
            resolved[1],
            resolved[0],
        )
        return resolved
    log.info("OIDC group mapping: no matching source group found in claim values")
    return None


def _resolve_default_user_group() -> tuple[int, str]:
    return oidc_groups.resolve_default_user_group()


def _resolve_display_name(claims: dict, username: str) -> str:
    return oidc_groups.resolve_display_name(claims, username)


def _log_oidc_config(cfg: dict[str, str]) -> None:
    oidc_config.log_oidc_config(cfg)


def _b64url_encode(data: bytes) -> str:
    return oidc_crypto.b64url_encode(data)


def _b64url_decode(data: str) -> bytes:
    return oidc_crypto.b64url_decode(data)


def _sign_state(payload: dict[str, object], secret: str) -> str:
    return oidc_crypto.sign_state(payload, secret)


def _verify_state(token: str, secret: str, max_age_seconds: int = 600) -> dict[str, object]:
    return oidc_crypto.verify_state(token, secret, max_age_seconds=max_age_seconds)


def _encrypt_state_value(value: str, secret: str) -> str:
    return oidc_crypto.encrypt_state_value(value, secret)


def _decrypt_state_value(token: str, secret: str) -> str:
    return oidc_crypto.decrypt_state_value(token, secret)


def _generate_pkce_pair() -> tuple[str, str]:
    return oidc_crypto.generate_pkce_pair()


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_oidc_metadata(issuer: str) -> dict:
    """Fetch and cache OIDC provider metadata for discovery endpoints."""
    discovery_url = f"{issuer}/.well-known/openid-configuration"
    log.info("Fetching OIDC metadata issuer=%s url=%s", issuer, discovery_url)
    response = requests.get(
        discovery_url,
        timeout=10,
        headers={"Accept": "application/json"},
    )
    log.info("OIDC metadata response status=%s url=%s", response.status_code, discovery_url)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        # Surface provider error details (Entra often returns AADSTS codes in body).
        body = (response.text or "").strip()
        snippet = body[:800]
        log.error(
            "OIDC metadata fetch failed status=%s url=%s body=%s",
            response.status_code,
            discovery_url,
            snippet,
        )
        raise RuntimeError(
            f"OIDC discovery failed ({response.status_code}) for {discovery_url}: {snippet or str(exc)}"
        ) from exc
    metadata = response.json()
    log.info(
        "OIDC metadata endpoints authorization=%s token=%s jwks=%s end_session=%s",
        metadata.get("authorization_endpoint"),
        metadata.get("token_endpoint"),
        metadata.get("jwks_uri"),
        metadata.get("end_session_endpoint"),
    )
    return metadata


def _validate_id_token(
    *,
    id_token: str,
    jwks_uri: str,
    issuer: str,
    client_id: str,
    expected_nonce: str,
) -> dict:
    """Validate ID token signature, issuer/audience, and nonce binding."""
    log.info(
        "Validating ID token jwks_uri=%s issuer=%s client_id=%s expected_nonce_present=%s",
        jwks_uri,
        issuer,
        client_id,
        bool(expected_nonce),
    )

    jwks_client = PyJWKClient(jwks_uri)
    signing_key = jwks_client.get_signing_key_from_jwt(id_token)
    log.info("Resolved signing key kid=%s", getattr(signing_key, "key_id", None))

    claims = jwt.decode(
        id_token,
        key=signing_key.key,
        algorithms=["RS256", "PS256", "ES256"],
        audience=client_id,
        issuer=issuer,
        options={"require": ["exp", "iat", "iss", "aud", "sub"]},
    )

    token_nonce = claims.get("nonce")
    log.info(
        "ID token decoded token_nonce_present=%s expected_nonce_present=%s",
        bool(token_nonce),
        bool(expected_nonce),
    )
    if token_nonce != expected_nonce:
        raise ValueError("Invalid OIDC nonce.")

    return claims


def _resolve_username(claims: dict) -> str:
    """Map validated OIDC claims to local Reporter username lookup key."""
    username = claims.get("preferred_username") or claims.get("email") or claims.get("sub")
    if not username:
        raise ValueError("No usable username claim found in ID token.")
    return str(username).strip()


def _seconds_left(ts: float | datetime | None) -> int | None:
    if ts is None:
        return None

    if isinstance(ts, datetime):
        ts = ts.timestamp()

    try:
        return max(0, int(ts - datetime.now(UTC).timestamp()))
    except (TypeError, ValueError):
        return None


def clear_oidc_callback_state(*, clear_query_params: bool = True) -> None:
    """Clear temporary callback-processing state keys."""
    log.info("Clearing OIDC callback state clear_query_params=%s", clear_query_params)
    st.session_state.pop(OIDC_LAST_CODE_KEY, None)
    st.session_state.pop(OIDC_PENDING_TOKEN_RESPONSE_KEY, None)
    st.session_state.pop(OIDC_PENDING_CLAIMS_KEY, None)
    st.session_state.pop(OIDC_PENDING_USERNAME_KEY, None)
    if clear_query_params:
        st.query_params.clear()


def clear_oidc_auth_state(*, clear_query_params: bool = False) -> None:
    """Clear persisted OIDC auth/session keys from Streamlit session state."""
    log.info("Clearing OIDC auth state clear_query_params=%s", clear_query_params)
    st.session_state.pop(OIDC_ID_TOKEN_KEY, None)
    st.session_state.pop(OIDC_ACCESS_TOKEN_KEY, None)
    st.session_state.pop(OIDC_REFRESH_TOKEN_KEY, None)
    st.session_state.pop(OIDC_EXPIRES_AT_KEY, None)
    st.session_state.pop(OIDC_REFRESH_EXPIRES_AT_KEY, None)
    st.session_state.pop(OIDC_ID_TOKEN_EXP_KEY, None)
    st.session_state.pop(OIDC_GROUP_CLAIM_PATH_KEY, None)
    st.session_state.pop(OIDC_GROUP_CLAIM_VALUES_KEY, None)
    st.session_state.pop(OIDC_GROUP_MAPPING_MATCH_KEY, None)
    clear_oidc_callback_state(clear_query_params=clear_query_params)


def has_oidc_callback_params() -> bool:
    """Return True when login page currently contains OIDC callback params."""
    code = st.query_params.get("code")
    state = st.query_params.get("state")
    error = st.query_params.get("error")
    has_callback = bool(code or error or state)
    log.info(
        "OIDC callback probe has_callback=%s has_code=%s has_state=%s error=%s query_keys=%s",
        has_callback,
        bool(code),
        bool(state),
        error,
        sorted(st.query_params.keys()),
    )
    return has_callback


def render_oidc_login(provider_name: str) -> None:
    """Render IdP login button with signed state and nonce."""
    try:
        cfg = _get_oidc_config(provider_name)
        _log_oidc_config(cfg)
        metadata = _fetch_oidc_metadata(cfg["issuer"])
    except Exception as exc:
        log.exception("OIDC configuration error during login render for provider=%s", provider_name)
        display_name = _get_provider_display_name(provider_name)
        # Keep UI errors short and actionable. Detailed errors are in logs.
        if isinstance(exc, requests.exceptions.Timeout):
            st.warning(f"{display_name} login is unavailable: IdP discovery timed out. Check network access to issuer.")
        elif isinstance(exc, requests.exceptions.ConnectionError):
            st.warning(
                f"{display_name} login is unavailable: IdP is not reachable from this environment. "
                "Check DNS/proxy/firewall or disable this provider in UI_AUTH_MODE."
            )
        elif isinstance(exc, requests.exceptions.HTTPError):
            status = getattr(getattr(exc, "response", None), "status_code", None)
            status_str = str(status) if status is not None else "HTTP error"
            st.warning(
                f"{display_name} login is unavailable: IdP discovery failed ({status_str}). "
                "Verify the issuer URL and tenant/cloud settings."
            )
        else:
            st.warning(
                f"{display_name} login is unavailable due to an OIDC configuration/discovery error. "
                "Check logs for details."
            )
        return

    nonce = secrets.token_urlsafe(32)
    code_verifier, code_challenge = _generate_pkce_pair()
    state_payload = {
        "nonce": nonce,
        "iat": int(time.time()),
        "provider": provider_name,
        "cv": _encrypt_state_value(code_verifier, cfg["state_secret"]),
    }
    state = _sign_state(state_payload, cfg["state_secret"])

    auth_params = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        # Keep callback params in query string so Streamlit can detect callback
        # via st.query_params and run complete_oidc_login().
        "response_mode": "query",
        "scope": cfg["scopes"],
        "state": state,
        "nonce": nonce,
        "prompt": cfg.get("prompt", "select_account"),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{metadata['authorization_endpoint']}?{urlencode(auth_params)}"

    log.info(
        "OIDC authorize request provider=%s authorization_endpoint=%s client_id=%s redirect_uri=%s scope=%s "
        "nonce_present=%s state_present=%s",
        provider_name,
        metadata["authorization_endpoint"],
        cfg["client_id"],
        cfg["redirect_uri"],
        cfg["scopes"],
        bool(nonce),
        bool(state),
    )
    _log_flow_step(
        0,
        "rendered IdP redirect provider=%s authorization_endpoint=%s",
        provider_name,
        metadata["authorization_endpoint"],
        branch="A",
    )

    display_name = _get_provider_display_name(provider_name)
    icon_svg = _get_provider_icon_svg(provider_name)
    icon_html = (
        '<span style="display:inline-flex; width:200px; height:2.8rem; flex:0 0 200px; '
        'align-items:center; justify-content:center;">'
        '<span style="display:inline-flex; width:100%; height:100%; '
        f'align-items:center; justify-content:center;">{icon_svg}</span>'
        "</span>"
        if icon_svg
        else ""
    )
    label_html = (
        '<span style="display:inline-flex; align-items:center; justify-content:center; width:100%;">'
        f"{icon_html}<span></span>"
        "</span>"
    )
    st.markdown(
        f'<a href="{html.escape(auth_url)}" target="_self">'
        f'<button style="width: 100%; padding: 0.5rem 1rem; margin-bottom: 0.5rem;">{label_html}</button>'
        "</a>",
        unsafe_allow_html=True,
    )


def complete_oidc_login() -> None:
    """Complete OIDC callback: exchange code, validate token, start Reporter session."""
    log.info("---- OIDC CALLBACK START ----")
    _log_flow_step(1, "callback start")
    log.info("Initial session state summary: %s", _session_state_oidc_summary())
    log.info(
        "Incoming query params has_code=%s has_state=%s error=%s has_session_state=%s has_iss=%s",
        bool(st.query_params.get("code")),
        bool(st.query_params.get("state")),
        st.query_params.get("error"),
        "session_state" in st.query_params,
        "iss" in st.query_params,
    )

    error = st.query_params.get("error")
    if error:
        error_description = st.query_params.get("error_description")
        clear_oidc_callback_state()
        log.error("OIDC error param=%s error_description=%s", error, error_description)
        st.error("OIDC login failed.")
        _log_flow_step(2, "provider returned error -> redirect login error=%s", error, branch="A")
        st.switch_page("pages/_0_Login.py")
        return
    _log_flow_step(2, "provider error check passed")

    code_param = st.query_params.get("code")
    state_param = st.query_params.get("state")

    if not code_param:
        log.error("Missing authorization code")
        clear_oidc_callback_state()
        st.error("Missing authorization code.")
        _log_flow_step(3, "missing authorization code -> redirect login", branch="A")
        st.switch_page("pages/_0_Login.py")
        return
    _log_flow_step(3, "authorization code present")

    code = str(code_param)
    returned_state = str(state_param) if state_param else ""

    log.info(
        "OIDC callback params received has_code=%s has_state=%s",
        bool(code_param),
        bool(state_param),
    )

    # Prevent Streamlit reruns/back-navigation from repeatedly processing one-time callback params.
    # We keep all required material in local variables and session_state from this point on.
    st.query_params.clear()

    if not returned_state:
        log.error("Missing OIDC state")
        clear_oidc_callback_state()
        st.error("Missing OIDC state.")
        _log_flow_step(4, "missing state -> redirect login", branch="A")
        st.switch_page("pages/_0_Login.py")
        return
    _log_flow_step(4, "state param present")

    token_response: dict | None = None
    claims: dict | None = None
    username: str | None = None

    if st.session_state.get(OIDC_LAST_CODE_KEY) == code:
        log.warning("OIDC callback re-entry detected")
        if st.session_state.get(keys.AUTHENTICATED, False):
            log.info("Code already processed and user is authenticated, redirecting to home")
            clear_oidc_callback_state()
            _log_flow_step(5, "duplicate callback and authenticated -> redirect home", branch="A")
            st.switch_page("pages/_1_Home.py")
            return

        if (
            st.session_state.get(OIDC_PENDING_TOKEN_RESPONSE_KEY) is not None
            and st.session_state.get(OIDC_PENDING_CLAIMS_KEY) is not None
            and st.session_state.get(OIDC_PENDING_USERNAME_KEY) is not None
        ):
            log.warning("Code already exchanged; resuming login from pending callback state")
            token_response = st.session_state[OIDC_PENDING_TOKEN_RESPONSE_KEY]
            claims = st.session_state[OIDC_PENDING_CLAIMS_KEY]
            username = st.session_state[OIDC_PENDING_USERNAME_KEY]
            log.info(
                "Pending callback state found token=%s claims=%s username=%s",
                bool(token_response),
                bool(claims),
                username,
            )
            _log_flow_step(5, "duplicate callback resumed from pending state", branch="C")
        else:
            log.warning(
                "Code already seen but no pending callback state; callback cannot be resumed",
            )
            clear_oidc_callback_state()
            st.error("Sign-in could not be resumed. Please sign in again.")
            _log_flow_step(5, "duplicate callback without pending state -> redirect login", branch="B")
            st.switch_page("pages/_0_Login.py")
            return

    try:
        # We need to peek at the state to know which provider we're dealing with
        # so we can get the correct state_secret for verification.
        if not returned_state:
            raise ValueError("Missing OIDC state")

        if "." not in returned_state:
            raise ValueError("Malformed OIDC state.")

        payload_b64, _ = returned_state.split(".", 1)
        payload_raw = _b64url_decode(payload_b64)
        payload_peek = json.loads(payload_raw.decode("utf-8"))
        provider_name = str(payload_peek.get("provider", "")).strip()

        if not provider_name:
            raise ValueError("OIDC state did not contain provider id")

        cfg = _get_oidc_config(provider_name)
        _log_oidc_config(cfg)

        state_payload = _verify_state(returned_state, cfg["state_secret"])
        expected_nonce = str(state_payload["nonce"])
        encrypted_code_verifier = str(state_payload.get("cv", ""))
        if not encrypted_code_verifier:
            raise ValueError("Missing PKCE verifier. Please start the login again.")
        code_verifier = _decrypt_state_value(encrypted_code_verifier, cfg["state_secret"])
        log.info(
            "Decoded state payload nonce_present=%s iat=%s pkce_present=%s",
            bool(expected_nonce),
            state_payload.get("iat"),
            bool(code_verifier),
        )
        _log_flow_step(6, "state verified provider=%s", provider_name)

        metadata = _fetch_oidc_metadata(cfg["issuer"])
        log.info(
            "Metadata loaded authorization=%s token=%s jwks=%s",
            metadata.get("authorization_endpoint"),
            metadata.get("token_endpoint"),
            metadata.get("jwks_uri"),
        )
        _log_flow_step(7, "provider metadata loaded provider=%s", provider_name)

        if token_response is None or claims is None or username is None:
            _log_flow_step(8, "starting token exchange")
            token_payload = {
                "grant_type": "authorization_code",
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "code": code,
                "redirect_uri": cfg["redirect_uri"],
                "code_verifier": code_verifier,
            }
            redacted_token_payload = {
                "grant_type": token_payload["grant_type"],
                "client_id": token_payload["client_id"],
                "client_secret_present": bool(token_payload["client_secret"]),
                "code_present": bool(token_payload["code"]),
                "redirect_uri": token_payload["redirect_uri"],
                "pkce_present": bool(code_verifier),
            }
            log.info("Token exchange request payload=%s", redacted_token_payload)

            response = requests.post(
                metadata["token_endpoint"],
                data=token_payload,
                timeout=10,
            )

            log.info(
                "Token response status=%s headers=%s",
                response.status_code,
                {
                    "content-type": response.headers.get("content-type"),
                    "x-ms-request-id": response.headers.get("x-ms-request-id"),
                    "x-ms-correlation-id": response.headers.get("x-ms-correlation-id"),
                    "client-request-id": response.headers.get("client-request-id"),
                },
            )

            if not response.ok:
                error_summary = _response_error_summary(response)
                log.error("Token exchange failed %s", error_summary)
                try:
                    payload = response.json()
                except Exception:
                    payload = {}

                error = str(payload.get("error") or "").strip().lower()
                error_codes = payload.get("error_codes") or []
                is_already_redeemed = error == "invalid_grant" and (
                    54005 in error_codes or "already redeemed" in str(payload.get("error_description") or "").lower()
                )
                if is_already_redeemed:
                    clear_oidc_callback_state()
                    st.error("Sign-in link was already used. Please start the login again.")
                    _log_flow_step(8, "authorization code already redeemed -> redirect login", branch="A")
                    st.switch_page("pages/_0_Login.py")
                    return

                raise ValueError(f"Token exchange failed: {error_summary}")

            token_response = response.json()
            log.info("Token response summary: %s", _token_response_summary(token_response))

            id_token = token_response.get("id_token")
            if not id_token:
                raise ValueError("Token response did not contain an ID token.")

            claims = _validate_id_token(
                id_token=str(id_token),
                jwks_uri=metadata["jwks_uri"],
                issuer=cfg["issuer"],
                client_id=cfg["client_id"],
                expected_nonce=expected_nonce,
            )
            log.info("Claims summary: %s", _claims_summary(claims))

            username = _resolve_username(claims)
            log.info("Resolved username_present=%s", bool(username))

            st.session_state[OIDC_PENDING_TOKEN_RESPONSE_KEY] = token_response
            st.session_state[OIDC_PENDING_CLAIMS_KEY] = claims
            st.session_state[OIDC_PENDING_USERNAME_KEY] = username
            st.session_state[OIDC_LAST_CODE_KEY] = code
            log.info("Stored pending callback state for rerun recovery")
            _log_flow_step(9, "id token validated and username resolved")
        else:
            _log_flow_step(8, "using pending token exchange results", branch="B")
            _log_flow_step(9, "using pending claims and username", branch="B")

        claim_path = _group_claim_name()
        claim_values = _claim_values(claims, claim_path)
        mapped_group = _resolve_mapped_user_group(provider_name, claims)
        st.session_state[OIDC_GROUP_CLAIM_PATH_KEY] = claim_path
        st.session_state[OIDC_GROUP_CLAIM_VALUES_KEY] = claim_values
        st.session_state[OIDC_GROUP_MAPPING_MATCH_KEY] = (
            {"group_id": mapped_group[0], "group_name": mapped_group[1]} if mapped_group is not None else None
        )
        user_row = oidc_callback.resolve_or_provision_user(
            st_module=st,
            provider_name=provider_name,
            claims=claims,
            username=username,
            mapped_group=mapped_group,
            auto_provision_enabled=_auto_provision_enabled,
            auto_provision_require_email=_auto_provision_require_email,
            allowed_email_domains=_allowed_email_domains,
            is_email_allowed=_is_email_allowed,
            resolve_default_user_group=_resolve_default_user_group,
            resolve_display_name=_resolve_display_name,
            clear_oidc_callback_state=lambda: clear_oidc_callback_state(),
            create_oidc_user_fn=create_oidc_user,
            get_user_for_login_fn=get_user_for_login,
            log=log,
            log_flow_step=_log_flow_step,
        )
        if user_row is None:
            return

        oidc_callback.persist_oidc_session(
            st_module=st,
            provider_name=provider_name,
            token_response=token_response,
            claims=claims,
            user_row=user_row,
            oidc_id_token_key=OIDC_ID_TOKEN_KEY,
            oidc_access_token_key=OIDC_ACCESS_TOKEN_KEY,
            oidc_refresh_token_key=OIDC_REFRESH_TOKEN_KEY,
            oidc_expires_at_key=OIDC_EXPIRES_AT_KEY,
            oidc_refresh_expires_at_key=OIDC_REFRESH_EXPIRES_AT_KEY,
            oidc_id_token_exp_key=OIDC_ID_TOKEN_EXP_KEY,
            seconds_left=_seconds_left,
            preview=_preview,
            session_state_oidc_summary=_session_state_oidc_summary,
            clear_oidc_callback_state=lambda: clear_oidc_callback_state(),
            authenticated_key=keys.AUTHENTICATED,
            hydrate_authenticated_state_fn=hydrate_authenticated_state,
            session_manager_obj=session_manager,
            log=log,
            log_flow_step=_log_flow_step,
        )

    except Exception as exc:
        log.exception("OIDC login failed exc=%s", exc)
        log.info("Failure state summary before cleanup: %s", _session_state_oidc_summary())
        clear_oidc_callback_state()
        st.error("OIDC login failed. Please try again or contact support.")
        _log_flow_step(14, "unhandled exception -> redirect login", branch="A")
        st.switch_page("pages/_0_Login.py")
