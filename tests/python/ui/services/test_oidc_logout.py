from __future__ import annotations

from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest

from ui.services.auth import oidc_logout


class _FakeResponse:
    def __init__(self, payload: dict[str, str]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return

    def json(self) -> dict[str, str]:
        return self._payload


@pytest.mark.unit
def test_build_oidc_logout_url_uses_discovery_end_session_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENTRA_OIDC_ISSUER", "https://login.microsoftonline.com/tenant/v2.0")
    monkeypatch.setenv("ENTRA_OIDC_CLIENT_ID", "client-123")
    monkeypatch.setenv("ENTRA_OIDC_POST_LOGOUT_REDIRECT_URI", "http://localhost:8501/")
    monkeypatch.setattr(
        oidc_logout.requests,
        "get",
        lambda *_args, **_kwargs: _FakeResponse(
            {"end_session_endpoint": "https://login.microsoftonline.com/tenant/oauth2/v2.0/logout"}
        ),
    )
    monkeypatch.setattr(oidc_logout, "st", SimpleNamespace(session_state={"oidc_id_token": "id-token"}))

    logout_url = oidc_logout._build_oidc_logout_url(provider_name="entra")

    assert logout_url is not None
    parsed = urlparse(logout_url)
    assert parsed.scheme == "https"
    assert parsed.path.endswith("/oauth2/v2.0/logout")
    params = parse_qs(parsed.query)
    assert params["client_id"] == ["client-123"]
    assert params["post_logout_redirect_uri"] == ["http://localhost:8501/"]
    assert params["id_token_hint"] == ["id-token"]


@pytest.mark.unit
def test_build_oidc_logout_url_returns_none_without_end_session_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENTRA_OIDC_ISSUER", "https://login.microsoftonline.com/tenant/v2.0")
    monkeypatch.setenv("ENTRA_OIDC_CLIENT_ID", "client-123")
    monkeypatch.setenv("ENTRA_OIDC_POST_LOGOUT_REDIRECT_URI", "http://localhost:8501/")
    monkeypatch.setattr(oidc_logout.requests, "get", lambda *_args, **_kwargs: _FakeResponse({}))

    logout_url = oidc_logout._build_oidc_logout_url(provider_name="entra")

    assert logout_url is None
