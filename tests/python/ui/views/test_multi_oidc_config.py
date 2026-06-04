from __future__ import annotations

from typing import TYPE_CHECKING
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

from ui.views.login import oidc

if TYPE_CHECKING:
    import pytest


def test_get_oidc_config_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default/unprefixed provider config is deprecated; provider id must be explicit."""
    try:
        oidc._get_oidc_config("oidc")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for deprecated provider id 'oidc'")


def test_get_oidc_config_prefixed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test OIDC config with provider-specific prefix."""
    monkeypatch.delenv("KEYCLOAK_OIDC_PROMPT", raising=False)
    env = {
        "KEYCLOAK_OIDC_ISSUER": "http://keycloak-issuer",
        "KEYCLOAK_OIDC_CLIENT_ID": "keycloak-id",
        "KEYCLOAK_OIDC_CLIENT_SECRET": "keycloak-secret",
        "KEYCLOAK_OIDC_REDIRECT_URI": "http://keycloak-redirect",
        "KEYCLOAK_OIDC_POST_LOGOUT_REDIRECT_URI": "http://keycloak-logout",
        "KEYCLOAK_OIDC_STATE_SECRET": "keycloak-state-secret",
        "KEYCLOAK_OIDC_SCOPES": "openid email",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    config = oidc._get_oidc_config("keycloak")
    assert config["issuer"] == "http://keycloak-issuer"
    assert config["client_id"] == "keycloak-id"
    assert config["client_secret"] == "keycloak-secret"
    assert config["scopes"] == "openid email"
    assert config["prompt"] == "login"
    assert config["state_secret"] == "keycloak-state-secret"


def test_get_oidc_config_prefixed_prompt_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provider-specific prompt should be loaded when explicitly configured."""
    env = {
        "ENTRA_OIDC_ISSUER": "http://entra-issuer",
        "ENTRA_OIDC_CLIENT_ID": "entra-id",
        "ENTRA_OIDC_CLIENT_SECRET": "entra-secret",
        "ENTRA_OIDC_REDIRECT_URI": "http://entra-redirect",
        "ENTRA_OIDC_POST_LOGOUT_REDIRECT_URI": "http://entra-logout",
        "ENTRA_OIDC_STATE_SECRET": "entra-state-secret",
        "ENTRA_OIDC_PROMPT": "select_account",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    config = oidc._get_oidc_config("entra")
    assert config["prompt"] == "select_account"


def test_get_provider_display_name() -> None:
    """Test mapping of provider IDs to display names."""
    assert oidc._get_provider_display_name("oidc") == "Oidc"
    assert oidc._get_provider_display_name("keycloak") == "Keycloak"
    assert oidc._get_provider_display_name("entra") == "Entra ID"
    assert oidc._get_provider_display_name("okta") == "Okta"
    assert oidc._get_provider_display_name("google") == "Google"
    assert oidc._get_provider_display_name("custom") == "Custom"


def test_auto_provision_require_email_default_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OIDC_AUTO_PROVISION_REQUIRE_EMAIL", raising=False)
    assert oidc._auto_provision_require_email() is True


def test_auto_provision_require_email_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OIDC_AUTO_PROVISION_REQUIRE_EMAIL", "false")
    assert oidc._auto_provision_require_email() is False


def test_claim_values_from_list_claim() -> None:
    claims = {"groups": ["idp-viewer", "idp-admin"]}
    assert oidc._claim_values(claims, "groups") == ["idp-viewer", "idp-admin"]


def test_claim_values_from_dotted_claim() -> None:
    claims = {"realm_access": {"roles": ["viewer", "admin"]}}
    assert oidc._claim_values(claims, "realm_access.roles") == ["viewer", "admin"]


def test_claim_values_missing_claim_returns_empty() -> None:
    claims = {"email": "user@example.com"}
    assert oidc._claim_values(claims, "groups") == []


def test_group_mapping_parses_valid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OIDC_GROUP_MAPPING", '{"idp-admin":"admin","idp-viewer":"viewer"}')
    assert oidc._group_mapping() == {"idp-admin": "admin", "idp-viewer": "viewer"}


def test_group_mapping_invalid_json_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OIDC_GROUP_MAPPING", "{not-json}")
    assert oidc._group_mapping() == {}


def test_resolve_mapped_user_group_matches_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OIDC_GROUP_CLAIM", "groups")
    monkeypatch.setenv("OIDC_GROUP_MAPPING", '{"idp-viewer":"viewer"}')
    monkeypatch.setattr(oidc, "_resolve_group_by_ref", lambda ref: (2, "viewer") if ref == "viewer" else None)

    claims = {"groups": ["idp-viewer"]}
    assert oidc._resolve_mapped_user_group("keycloak", claims) == (2, "viewer")


def test_resolve_mapped_user_group_no_match_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OIDC_GROUP_CLAIM", "groups")
    monkeypatch.setenv("OIDC_GROUP_MAPPING", '{"idp-viewer":"viewer"}')
    monkeypatch.setattr(oidc, "_resolve_group_by_ref", lambda _ref: (2, "viewer"))

    claims = {"groups": ["idp-unknown"]}
    assert oidc._resolve_mapped_user_group("keycloak", claims) is None


def test_resolve_mapped_user_group_target_missing_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OIDC_GROUP_CLAIM", "groups")
    monkeypatch.setenv("OIDC_GROUP_MAPPING", '{"idp-admin":"admin"}')
    monkeypatch.setattr(oidc, "_resolve_group_by_ref", lambda _ref: None)

    claims = {"groups": ["idp-admin"]}
    assert oidc._resolve_mapped_user_group("keycloak", claims) is None


def test_group_claim_name_fallback_from_idc_typo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OIDC_GROUP_CLAIM", raising=False)
    monkeypatch.setenv("IDC_GROUP_CLAIM", "realm_access.roles")
    assert oidc._group_claim_name() == "realm_access.roles"


def test_complete_oidc_login_existing_user_not_altered_by_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    class _QueryParams(dict):
        def clear(self) -> None:  # noqa: D401
            super().clear()

    state_payload = oidc._b64url_encode(b'{"provider":"keycloak"}')

    switch_calls: list[str] = []
    state = f"{state_payload}.sig"
    st_stub = SimpleNamespace(
        session_state={},
        query_params=_QueryParams({"code": "auth-code", "state": state}),
        error=lambda *_args, **_kwargs: None,
        info=lambda *_args, **_kwargs: None,
        warning=lambda *_args, **_kwargs: None,
        rerun=lambda: (_ for _ in ()).throw(AssertionError("rerun should not be called")),
        switch_page=lambda page: switch_calls.append(page),
    )
    monkeypatch.setattr(oidc, "st", st_stub)

    monkeypatch.setattr(
        oidc,
        "_get_oidc_config",
        lambda _provider: {
            "state_secret": "secret",
            "issuer": "iss",
            "client_id": "cid",
            "client_secret": "csec",
            "redirect_uri": "http://localhost/0_Login",
            "post_logout_redirect_uri": "http://localhost/",
            "scopes": "openid profile email",
        },
    )
    monkeypatch.setattr(
        oidc,
        "_verify_state",
        lambda _state, _secret: {"nonce": "nonce", "provider": "keycloak", "iat": 1, "cv": "encrypted-verifier"},
    )
    monkeypatch.setattr(
        oidc,
        "_decrypt_state_value",
        lambda token, _secret: "pkce-verifier" if token == "encrypted-verifier" else "",
    )
    monkeypatch.setattr(
        oidc,
        "_fetch_oidc_metadata",
        lambda _issuer: {"token_endpoint": "https://idp/token", "jwks_uri": "https://idp/jwks"},
    )
    monkeypatch.setattr(oidc, "_validate_id_token", lambda **_kwargs: {"sub": "sub-1", "exp": 9999999999})
    monkeypatch.setattr(oidc, "_resolve_username", lambda _claims: "existing-user")
    monkeypatch.setattr(oidc, "_resolve_mapped_user_group", lambda _provider, _claims: (2, "viewer"))
    monkeypatch.setattr(oidc, "hydrate_authenticated_state", lambda _user: None)
    monkeypatch.setattr(oidc.session_manager, "start_session", lambda **_kwargs: "session-token")
    monkeypatch.setattr(oidc.session_manager, "get_session_token", lambda: "session-token")

    create_oidc_user_mock = MagicMock(return_value=(True, "created"))
    monkeypatch.setattr(oidc, "create_oidc_user", create_oidc_user_mock)

    get_user_calls: list[str] = []

    def _get_user_for_login(username: str) -> dict[str, object]:
        get_user_calls.append(username)
        return {
            "id": 42,
            "name": "existing-user",
            "display_name": "Existing User",
            "is_admin": False,
            "has_profile": True,
            "user_group_id": 1,
            "group_name": "admin",
        }

    monkeypatch.setattr(oidc, "get_user_for_login", _get_user_for_login)

    class _FakeResponse:
        ok = True
        status_code = 200
        text = ""
        headers = {"content-type": "application/json"}

        @staticmethod
        def json() -> dict[str, object]:
            return {
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "id_token": "id-token",
                "expires_in": 3600,
                "refresh_expires_in": 7200,
            }

    token_payloads: list[dict[str, str]] = []

    def _post(_url: str, *, data: dict[str, str], **_kwargs: object) -> _FakeResponse:
        token_payloads.append(data)
        return _FakeResponse()

    monkeypatch.setattr(oidc.requests, "post", _post)

    oidc.complete_oidc_login()

    # Existing user path should not auto-provision or alter user-group membership.
    assert create_oidc_user_mock.call_count == 0
    assert get_user_calls == ["existing-user"]
    assert token_payloads[0]["code_verifier"] == "pkce-verifier"
    assert switch_calls == ["pages/_1_Home.py"]


def test_render_oidc_login_encrypts_pkce_verifier_in_state(monkeypatch: pytest.MonkeyPatch) -> None:
    rendered: list[str] = []
    signed_payloads: list[dict[str, object]] = []

    st_stub = SimpleNamespace(
        session_state={},
        markdown=lambda html, **_kwargs: rendered.append(html),
        warning=lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(oidc, "st", st_stub)
    monkeypatch.setattr(oidc, "_log_oidc_config", lambda _cfg: None)
    monkeypatch.setattr(
        oidc,
        "_get_oidc_config",
        lambda _provider: {
            "state_secret": "secret",
            "issuer": "https://issuer",
            "client_id": "client-id",
            "client_secret": "client-secret",
            "redirect_uri": "https://app/callback",
            "post_logout_redirect_uri": "https://app/",
            "scopes": "openid profile email",
            "prompt": "login",
        },
    )
    monkeypatch.setattr(
        oidc,
        "_fetch_oidc_metadata",
        lambda _issuer: {"authorization_endpoint": "https://idp/authorize"},
    )
    monkeypatch.setattr(oidc, "_generate_pkce_pair", lambda: ("pkce-verifier", "pkce-challenge"))
    monkeypatch.setattr(
        oidc,
        "_encrypt_state_value",
        lambda value, _secret: "encrypted-verifier" if value == "pkce-verifier" else "",
    )

    def _sign_state(payload: dict[str, object], _secret: str) -> str:
        signed_payloads.append(payload)
        return "signed-state"

    monkeypatch.setattr(oidc, "_sign_state", _sign_state)

    oidc.render_oidc_login("keycloak")

    assert signed_payloads
    assert signed_payloads[0]["cv"] == "encrypted-verifier"
    assert "pkce-verifier" not in str(signed_payloads[0])
    assert st_stub.session_state == {}

    auth_url = rendered[0].split('href="', 1)[1].split('"', 1)[0]
    params = parse_qs(urlparse(auth_url).query)
    assert params["code_challenge"] == ["pkce-challenge"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["state"] == ["signed-state"]
