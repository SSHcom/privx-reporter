"""Tests for password hashing and validation utilities."""

import pytest

from ui.utils.password import hash_password, validate_password, validate_password_policy


@pytest.mark.unit
def test_hash_password_returns_valid_bcrypt_hash() -> None:
    """Test that hash_password returns a valid bcrypt hash string."""
    result = hash_password("test_password")
    assert isinstance(result, str)
    assert result.startswith("$2b$")
    assert len(result) == 60


@pytest.mark.unit
def test_hash_password_produces_different_hashes() -> None:
    """Test that hashing the same password produces different hashes (due to salt)."""
    password = "same_password"
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    assert hash1 != hash2


@pytest.mark.unit
def test_validate_password_correct() -> None:
    """Test that validate_password returns True for correct password."""
    password = "correct_password"
    hashed = hash_password(password)
    assert validate_password(password, hashed) is True


@pytest.mark.unit
def test_validate_password_incorrect() -> None:
    """Test that validate_password returns False for incorrect password."""
    password = "correct_password"
    hashed = hash_password(password)
    assert validate_password("wrong_password", hashed) is False


@pytest.mark.unit
def test_validate_password_empty_password() -> None:
    """Test that validate_password handles empty password."""
    hashed = hash_password("some_password")
    assert validate_password("", hashed) is False


@pytest.mark.unit
def test_hash_password_empty() -> None:
    """Test that hash_password can hash an empty string."""
    result = hash_password("")
    assert isinstance(result, str)
    assert result.startswith("$2b$")


@pytest.mark.unit
def test_validate_password_non_bcrypt_hash_returns_false() -> None:
    """Test that validate_password fails closed for non-bcrypt hash-like values."""
    assert validate_password("anything", "OIDC") is False


@pytest.mark.unit
def test_validate_password_policy_accepts_valid_password() -> None:
    ok, message = validate_password_policy("ValidPass!")
    assert ok is True
    assert message == ""


@pytest.mark.unit
def test_validate_password_policy_rejects_short_password() -> None:
    ok, message = validate_password_policy("Aa!1234")
    assert ok is False
    assert "at least 8 characters" in message.lower()


@pytest.mark.unit
def test_validate_password_policy_allows_missing_uppercase() -> None:
    ok, message = validate_password_policy("validpass!")
    assert ok is True
    assert message == ""


@pytest.mark.unit
def test_validate_password_policy_rejects_missing_special_character() -> None:
    ok, message = validate_password_policy("ValidPass1")
    assert ok is False
    assert "special character" in message.lower()
