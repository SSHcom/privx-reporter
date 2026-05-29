"""Tests for OIDC crypto helpers."""

import time

import pytest

from ui.views.login.oidc_crypto import (
    b64url_decode,
    b64url_encode,
    decrypt_state_value,
    encrypt_state_value,
    generate_pkce_pair,
    sign_state,
    verify_state,
)


@pytest.mark.unit
def test_b64url_encode_decode_roundtrip() -> None:
    original = b"test data with special chars: +/="
    encoded = b64url_encode(original)
    decoded = b64url_decode(encoded)
    assert decoded == original


@pytest.mark.unit
def test_generate_pkce_pair_produces_valid_lengths() -> None:
    verifier, challenge = generate_pkce_pair()
    assert 43 <= len(verifier) <= 128
    assert len(challenge) == 43


@pytest.mark.unit
def test_sign_state_verify_state_roundtrip() -> None:
    payload = {"nonce": "abc123", "iat": int(time.time())}
    secret = "test-secret"
    token = sign_state(payload, secret)
    recovered = verify_state(token, secret)
    assert recovered["nonce"] == "abc123"


@pytest.mark.unit
def test_verify_state_rejects_tampered_signature() -> None:
    payload = {"nonce": "abc", "iat": int(time.time())}
    token = sign_state(payload, "secret")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(ValueError, match="signature"):
        verify_state(tampered, "secret")


@pytest.mark.unit
def test_verify_state_rejects_expired_state() -> None:
    payload = {"nonce": "abc", "iat": int(time.time()) - 700}
    token = sign_state(payload, "secret")
    with pytest.raises(ValueError, match="expired"):
        verify_state(token, "secret", max_age_seconds=600)


@pytest.mark.unit
def test_encrypt_decrypt_state_value_roundtrip() -> None:
    value = "pkce-verifier-12345"
    secret = "encryption-key"
    encrypted = encrypt_state_value(value, secret)
    decrypted = decrypt_state_value(encrypted, secret)
    assert decrypted == value
