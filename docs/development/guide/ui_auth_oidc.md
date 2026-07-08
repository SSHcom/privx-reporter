# UI Auth and OIDC

This document describes developer-relevant authentication flow for the UI, including local login and OIDC.

It focuses on implementation behavior and extension points, not operations troubleshooting depth.

## Auth Mode Selection

Local login is always available. OIDC providers are enabled via:

- `OIDC_1_ENABLED=true` - Enable OIDC provider 1
- `OIDC_2_ENABLED=true` - Enable OIDC provider 2

Routing and rendering are handled in `apps/python/ui/pages/_0_Login.py`:

- local login form via `_render_local_login()` (always rendered)
- provider buttons via `render_oidc_login(provider)` for enabled providers

## Local Login Flow

Local flow in `_0_Login.py`:

1. User submits username/password.
2. UI validates credentials from admin DB user row.
3. Session state is hydrated (`hydrate_authenticated_state`).
4. `session_manager.start_session(..., auth_source="local")`.
5. Redirect to Home.

## OIDC Login Flow

OIDC flow is implemented in `apps/python/ui/views/login/oidc.py`.

High-level path:

1. Login page renders provider button (`render_oidc_login`).
2. OIDC discovery metadata is loaded from issuer.
3. UI creates nonce + PKCE pair (`code_verifier`, `S256 code_challenge`).
4. UI signs state payload and includes provider + nonce + encrypted PKCE verifier.
5. Browser is redirected to IdP authorization endpoint.
6. Callback returns to login page with `code` and `state`.
7. Callback verifies signed state, decrypts PKCE verifier, exchanges code for tokens.
8. ID token is validated (JWKS signature, issuer, audience, nonce, required claims).
9. Local username is resolved (`preferred_username`, then `email`, then `sub`).
10. User is resolved/provisioned and Reporter session is started.

## Callback and Rerun Safety

Login callback path intentionally runs before normal page bootstrap restore:

- `_0_Login.py` detects callback params and calls `_setup_callback_page()`
- callback clears query params early
- duplicate callback/rerun handling uses pending state keys to avoid token re-exchange issues

This prevents Streamlit reruns from corrupting callback progress.

## User Resolution and Optional Auto-Provision

User resolution/provision finalize is delegated to `apps/python/ui/views/login/oidc_callback.py`:

- `resolve_or_provision_user(...)`
- `persist_oidc_session(...)`

Behavior:

- existing local users are reused
- if missing and auto-provision disabled -> login fails closed
- if auto-provision enabled -> creates local user in mapped/default group
- group mapping is applied only during creation, not retroactive updates

OIDC configuration values are read via `lib.service.env_source.getEnv()` (env or DB-backed, depending on `ENV_SOURCE`) and centralized in `apps/python/lib/env_oidc.py`.
`apps/python/ui/views/login/oidc_config.py` focuses on provider presentation loading (name/icon/discovery), while `apps/python/ui/views/login/oidc_groups.py` handles optional group-claim mapping.

## Session Model

Session model is managed by `apps/python/ui/services/session/session_manager.py`:

1. Reporter session: cookie token + DB-backed session row.
2. OIDC session: persisted token material and expiry timestamps for restore/refresh.

`auth_source` values:

- `local`
- `oidc:1` (OIDC provider 1)
- `oidc:2` (OIDC provider 2)

Key restore behavior:

- restore requires valid Reporter session and valid auth-source model
- OIDC access refresh is attempted near expiry
- refresh failure ends Reporter session (fail-closed)
- only allowed auth sources (`local` + enabled OIDC providers) are accepted on restore

## Security-Critical Contracts

When changing auth/OIDC code, preserve these behaviors:

- signed and age-checked `state` verification
- nonce generation and validation
- PKCE (`S256`) for authorization code flow
- strict ID token validation against issuer/audience/signature
- fail-closed handling on callback/token/user resolution failures
- no raw token/secret logging
- end local session if OIDC refresh cannot maintain session validity

## Main Auth/OIDC Files

- `apps/python/ui/pages/_0_Login.py`
- `apps/python/ui/views/login/oidc.py`
- `apps/python/ui/views/login/oidc_callback.py`
- `apps/python/ui/views/login/oidc_config.py`
- `apps/python/lib/env_oidc.py`
- `apps/python/ui/views/login/oidc_crypto.py`
- `apps/python/ui/views/login/oidc_groups.py`
- `apps/python/ui/services/session/session_manager.py`
- `apps/python/ui/services/auth/oidc_refresh.py`
- `apps/python/ui/services/auth/oidc_logout.py`

## Operations References

- [OIDC UI Authentication Guide](../../operations/OIDC_UI_AUTH_GUIDE.md)
- [UI Operational Guide](../../operations/UI_ADMIN_GUIDE.md)
- [Environment Variables](../../operations/ENVIRONMENT_VARIABLES.md)

## Links

- Next: [UI OIDC login success path](ui_oidc_login_success_path.md)
- [Back to development guide](../DEVELOPMENT_GUIDE.md)
