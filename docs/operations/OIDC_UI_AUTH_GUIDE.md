# OIDC UI Authentication Guide

This guide covers how to enable, operate, and troubleshoot OIDC-based login for the Reporter UI.

For implementation structure and code flow, see [UI auth and OIDC](../development/guide/ui_auth_oidc.md) and [UI OIDC login success path](../development/guide/ui_oidc_login_success_path.md).

## Scope

This guide covers:

- Switching UI auth mode to OIDC
- Required environment variables
- Provider-specific notes
- Local user mapping and optional auto-provisioning
- Session and logout behavior
- Common troubleshooting cases

## Auth Modes

UI auth mode is controlled by:

- `UI_AUTH_MODE=local` (default behavior)
- `UI_AUTH_MODE=local,keycloak`
- `UI_AUTH_MODE=local,keycloak,entra` (multiple OIDC providers)

Notes:

- `AUTH_MODE` is not used by current UI auth routing.
- `UI_AUTH_MODE` is a comma-separated list. `local` enables username+password login. Any other entry is treated as an OIDC provider id and gets a separate login button.

## Required OIDC Environment Variables

Set these for each OIDC provider `X` enabled in `UI_AUTH_MODE` (variables are prefixed with the provider id in uppercase):

- `X_OIDC_ISSUER`
- `X_OIDC_CLIENT_ID`
- `X_OIDC_CLIENT_SECRET`
- `X_OIDC_REDIRECT_URI`
- `X_OIDC_POST_LOGOUT_REDIRECT_URI`
- `X_OIDC_STATE_SECRET` - used to sign and validate the OIDC `state` parameter for CSRF protection; the `state` value is signed, not encrypted

Optional:

- `X_OIDC_SCOPES` (default: `openid profile email`)
- `X_OIDC_PROMPT` (default: `login`) - OIDC `prompt` parameter sent on the authorization request; set a provider-specific override such as `select_account` when needed

Current implementation note:

- Reporter implements the OpenID Connect Authorization Code Flow as a confidential client, without PKCE.
- Reporter currently uses a server-side authorization code flow with `client_secret` during token exchange.
- PKCE (`code_verifier`, `code_challenge`) is not currently implemented. In the current Reporter flow, this is acceptable because Reporter acts as a confidential client and performs the authorization code token exchange server-side using a client secret.
- Operationally, configure the IdP client as a confidential client that is allowed to use the configured redirect URI.

### Provider Prefix Rules

- For provider id `X` (for example `keycloak`, `entra`), set `X_OIDC_*` variables (uppercased): `KEYCLOAK_OIDC_ISSUER`, `ENTRA_OIDC_CLIENT_ID`, and so on.
- Each provider needs its own `*_OIDC_STATE_SECRET` for `state` signing and validation. This protects integrity, not confidentiality.

Example:

```env
UI_AUTH_MODE=local,keycloak,entra

KEYCLOAK_OIDC_ISSUER=http://localhost:8080/realms/reporter
KEYCLOAK_OIDC_CLIENT_ID=reporter-local
KEYCLOAK_OIDC_CLIENT_SECRET=<client-secret>
KEYCLOAK_OIDC_REDIRECT_URI=http://localhost:8501/0_Login
KEYCLOAK_OIDC_POST_LOGOUT_REDIRECT_URI=http://localhost:8501/
KEYCLOAK_OIDC_SCOPES="openid profile email"
KEYCLOAK_OIDC_PROMPT=login
KEYCLOAK_OIDC_STATE_SECRET=<long-random-secret>

ENTRA_OIDC_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0
ENTRA_OIDC_CLIENT_ID=<app-client-id>
ENTRA_OIDC_CLIENT_SECRET=<client-secret>
ENTRA_OIDC_REDIRECT_URI=http://localhost:8501/0_Login
ENTRA_OIDC_POST_LOGOUT_REDIRECT_URI=http://localhost:8501/
ENTRA_OIDC_SCOPES="openid profile email offline_access"
ENTRA_OIDC_PROMPT=login
ENTRA_OIDC_STATE_SECRET=<long-random-secret>
```

## Provider Notes

### Keycloak

- Typical issuer format: `http(s)://<host>/realms/<realm>`
- Redirect URI in the Keycloak client must exactly match `X_OIDC_REDIRECT_URI`.
- Post-logout redirect URI must be allowed in the Keycloak client settings.
- Common username mapping:
  - `preferred_username`
  - fallback `email`

### Microsoft Entra ID

- Typical issuer format: `https://login.microsoftonline.com/<tenant-id>/v2.0`
- The app registration must allow the exact redirect URI used by Reporter.
- If using logout redirect, ensure the post-logout URI is configured in the app registration.
- Common mapping choices:
  - `preferred_username`
  - `email`
  - `sub` fallback exists but is usually not human-friendly
- During logout, Entra may still prompt for session or account selection even when `id_token_hint` is sent. This can happen when multiple Entra sessions exist in the browser, or when Entra cannot silently bind the logout request to a single active session.

## Local User Mapping Requirement

Reporter resolves the local username from OIDC claims in this order:

1. `preferred_username`
2. `email`
3. `sub`

By default, OIDC requires that a matching Reporter local user already exists in the admin DB.

Reporter uses a shared username namespace across all authentication methods. By default, usernames resolved from OIDC claims must match existing local usernames in Reporter. If OIDC auto-provisioning is enabled, Reporter can create the missing local user instead.

If multiple OIDC providers are enabled and they are intended to authenticate the same Reporter user, the resolved username should be the same across those providers. Reporter does not isolate identities per provider; it maps all providers into the same local username namespace.

- The resolved OIDC username must match an existing Reporter user in the admin DB.
- If no user is found, login is rejected with a user-facing error.

Operational recommendation:

- Create Reporter local usernames that match your IdP claim strategy.
- Keep mapping consistent across users to avoid failed local-user lookups.

Warning:

- `sub` is the only generally stable unique identifier across sessions.
- Using `preferred_username` or `email` for local user mapping can break if IdP user attributes change.
- This is especially relevant for providers where email-like aliases may change over time.

## Optional Auto-Provisioning

Reporter can auto-provision missing local users after a successful IdP login when enabled:

- `OIDC_AUTO_PROVISION=true`
- `OIDC_AUTO_PROVISION_DEFAULT_ROLE=<user_group name or id>` (must not be `admin` or `superadmin`)
- `OIDC_AUTO_PROVISION_REQUIRE_EMAIL=true|false` (default `true` when unset)
- `OIDC_AUTO_PROVISION_ALLOWED_EMAIL_DOMAINS=example.com,example.org` (optional allowlist; empty means allow all)

If `OIDC_AUTO_PROVISION_ALLOWED_EMAIL_DOMAINS` is set, `OIDC_AUTO_PROVISION_REQUIRE_EMAIL` must be `true`.

Operationally, an `email` claim is required for the domain allowlist check to run.

### Optional Group Claim Mapping

Reporter can map IdP group or role claims to an existing local Reporter `user_group` for auto-provisioned users.

- `OIDC_GROUP_CLAIM=<claim path>` (default: `groups`)
- `OIDC_GROUP_MAPPING='{"idp-group":"reporter_group"}'` (JSON object)

Examples:

- `OIDC_GROUP_CLAIM=groups`
- `OIDC_GROUP_CLAIM=realm_access.roles`
- `OIDC_GROUP_MAPPING='{"idp-admin":"admin","idp-viewer":"viewer"}'`

Behavior:

- Mapping is evaluated after claims are validated.
- If a mapped target group exists in the Reporter DB, auto-provision uses that group.
- If multiple IdP groups match, the first matching value in the claim list is used.
- Order is evaluated as received from the IdP claim array.
- If mapping does not match, or the mapped target group does not exist, auto-provision falls back to `OIDC_AUTO_PROVISION_DEFAULT_ROLE`.
- Reporter does not create new local groups from IdP claims.
- Existing local users are not altered by this mapping.
- IdP group mapping is applied only when Reporter auto-provisions a new local user. If the user's group changes later in the IdP, Reporter does not update the existing local user's Reporter `user_group` automatically. To apply the new mapping, update the `user_group` in Reporter manually, or remove and recreate the local user so auto-provisioning runs again.

## Session and Logout Behavior

Reporter keeps:

- Browser session cookie token
- DB-backed UI session row

For OIDC sessions, Reporter also tracks:

- refresh token
- ID token
- access and refresh expiry timestamps

Reporter stores the authentication source in `session.auth_source`. Current values are `local` or provider-qualified OIDC values such as `oidc:keycloak` or `oidc:entra`. This field is used to determine OIDC session restore, refresh, and logout behavior.

Important behavior:

- Reporter session validity does not override IdP validity.
- OIDC refresh is attempted before access token expiry.
- If refresh fails, Reporter ends the local session.
- If both the access token and refresh token have expired, the user must reauthenticate via the IdP.
- Logout clears local session state and token cookie, then performs front-channel logout using the provider `end_session_endpoint` when the auth source is OIDC.
- Logout includes `id_token_hint` when an ID token is available in session state.

## Security Logging Notes

Current OIDC logging avoids writing:

- raw token response bodies
- client secret values in payload logs
- full authorization code or state values
- full claim payload dumps

Masked previews and claim summaries are used instead.

## Troubleshooting

### Provider button does not render and an IdP discovery error is shown

Reporter fetches `{issuer}/.well-known/openid-configuration` while rendering the login page.

If the IdP is not reachable from the current environment, or the issuer is wrong, Reporter shows a warning and does not render the provider button.

Operational note:

- This means a temporary IdP outage can make the login option disappear from the UI.
- Consider whether hiding the provider button is the desired behavior for your deployment, versus showing it with a degraded or error state.

Check:

- the issuer URL is correct
- the UI runtime can reach the IdP
- the deployment should still expose that provider in `UI_AUTH_MODE`

### `invalid_grant` or `Code not valid`

Check:

- redirect URI exact match between IdP client config and `X_OIDC_REDIRECT_URI`
- callback code was not reused after a previous exchange
- system clocks are in sync

### Missing `session.auth_source` or OIDC session columns

The runtime session repository includes a schema backfill step for legacy databases. If migration still fails, check:

- the app is connected to the expected admin DB
- the DB role has `ALTER TABLE` permission on `session`

### OIDC login succeeds at the IdP but Reporter rejects the user

Check:

- the Reporter user exists for the resolved username claim
- the IdP user profile contains the expected `preferred_username`, `email`, or `sub` value
- auto-provision settings are actually enabled if that is the intended path

### Cookie mismatch logs after login

Short-term mismatch can occur during Streamlit rerun timing. Session restore has a grace path to avoid false logout loops.
