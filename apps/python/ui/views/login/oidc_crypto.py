"""State signing/verification helpers for OIDC callback CSRF protection."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from cryptography.fernet import Fernet, InvalidToken
from streamlit.logger import get_logger

log = get_logger(__name__)


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def generate_pkce_pair() -> tuple[str, str]:
    """Generate a PKCE code_verifier and code_challenge (S256 method).

    Returns (code_verifier, code_challenge).  The verifier must be included
    in the token exchange; the challenge goes in the authorization request.
    """
    code_verifier = secrets.token_urlsafe(32)  # 43 URL-safe chars (within 43-128 limit)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = b64url_encode(digest)
    return code_verifier, code_challenge


def _fernet(secret: str) -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_state_value(value: str, secret: str) -> str:
    """Encrypt a sensitive value for transport inside OIDC state."""
    return _fernet(secret).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_state_value(token: str, secret: str) -> str:
    """Decrypt a sensitive value from OIDC state."""
    try:
        return _fernet(secret).decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted OIDC state value.") from exc


def sign_state(payload: dict[str, object], secret: str) -> str:
    """Create compact signed state token `<payload>.<signature>`."""
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = b64url_encode(payload_json)
    signature = hmac.new(
        secret.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    signature_b64 = b64url_encode(signature)
    return f"{payload_b64}.{signature_b64}"


def verify_state(token: str, secret: str, max_age_seconds: int = 600) -> dict[str, object]:
    """Validate state signature and freshness, then return decoded payload."""
    token = token.strip()
    if "." not in token:
        raise ValueError("Malformed OIDC state.")

    payload_b64, signature_b64 = token.split(".", 1)
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    actual_sig = b64url_decode(signature_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid OIDC state signature.")

    payload_raw = b64url_decode(payload_b64)
    payload = json.loads(payload_raw.decode("utf-8"))
    issued_at = int(payload.get("iat", 0))
    now = int(time.time())
    age_seconds = now - issued_at
    log.info("OIDC state verification issued_at=%s now=%s age_seconds=%s", issued_at, now, age_seconds)
    if issued_at <= 0 or age_seconds > max_age_seconds:
        raise ValueError("OIDC state has expired.")
    return payload
