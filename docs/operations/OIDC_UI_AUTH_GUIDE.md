# OIDC UI Authentication Guide

This guide covers how to enable, operate, and troubleshoot OIDC-based login for the Reporter UI.

For implementation structure and code flow, see [UI auth and OIDC](../development/guide/ui_auth_oidc.md) and [UI OIDC login success path](../development/guide/ui_oidc_login_success_path.md).

## Scope

This guide covers:

- Enabling OIDC providers
- Required environment variables
- Provider-specific notes
- Local user mapping and optional auto-provisioning
- Session and logout behavior
- Common troubleshooting cases

## Enabling OIDC Providers

Reporter supports up to two OIDC providers. Local login is always available.

Enable providers using these settings:

- `OIDC_1_ENABLED=true` - Enable OIDC provider 1
- `OIDC_2_ENABLED=true` - Enable OIDC provider 2

Each enabled provider appears as a login button on the login page.

Optional UI behavior:

- `UI_COLLAPSE_LOCAL_LOGIN=true` shows local login in a collapsible section below OIDC buttons when at least one provider is enabled.

Common slot patterns:

- Single provider: `OIDC_1_ENABLED=true`, `OIDC_2_ENABLED=false`
- Two providers: `OIDC_1_ENABLED=true`, `OIDC_2_ENABLED=true`

## Configuration Location (`ENV_SOURCE`)

- `ENV_SOURCE=db`: configure OIDC values in Admin UI -> App Config.
- `ENV_SOURCE=env`: configure OIDC values in `.env` and expose the same keys under `reporter-ui -> environment` in `docker-compose-env.yml`.

For `ENV_SOURCE=env`:

- Uncomment enable flags and the active provider slot variables in `docker-compose-env.yml`.
- Leave unused provider slot variables commented (for example keep `OIDC_2_*` commented when `OIDC_2_ENABLED=false`).
- Optional global OIDC variables (`OIDC_AUTO_PROVISION*`, `OIDC_GROUP_*`) should stay unset/commented if you do not use those features.

## Required OIDC Environment Variables

For each enabled provider slot (1 or 2), set these variables:

- `OIDC_<n>_NAME` - Display name shown on the login button (e.g. "Keycloak", "Entra ID")
- `OIDC_<n>_ICON` - SVG icon file name (e.g. `Keycloak.svg`, `EntraID.svg`, `Generic-OpenID.svg`)
- `OIDC_<n>_ISSUER` - OIDC issuer URL
- `OIDC_<n>_CLIENT_ID` - Client ID from the IdP app registration
- `OIDC_<n>_CLIENT_SECRET` - Client secret from the IdP app registration
- `OIDC_<n>_REDIRECT_URI` - Must match IdP app registration exactly
- `OIDC_<n>_POST_LOGOUT_REDIRECT_URI` - Where to redirect after logout
- `OIDC_<n>_STATE_SECRET` - Long random secret for CSRF protection

Optional:

- `OIDC_<n>_SCOPES` (default: `openid profile email`)
- `OIDC_<n>_PROMPT` (default: `login`) - OIDC `prompt` parameter; use `select_account` for Entra if needed

Current implementation note:

- Reporter implements OpenID Connect Authorization Code Flow with PKCE (`S256`) and state+nonce validation.
- Reporter uses a confidential client and includes `client_secret` during token exchange.
- Operationally, configure the IdP client as a confidential client that is allowed to use the configured redirect URI.

### Example Configuration

```env
OIDC_1_ENABLED=true
OIDC_1_NAME=Keycloak
OIDC_1_ICON=Keycloak.svg
OIDC_1_ISSUER=http://localhost:8080/realms/reporter
OIDC_1_CLIENT_ID=reporter-local
OIDC_1_CLIENT_SECRET=<client-secret>
OIDC_1_REDIRECT_URI=http://localhost:8501/0_Login
OIDC_1_POST_LOGOUT_REDIRECT_URI=http://localhost:8501/
OIDC_1_SCOPES="openid profile email"
OIDC_1_PROMPT=login
OIDC_1_STATE_SECRET=<long-random-secret>

OIDC_2_ENABLED=true
OIDC_2_NAME=Entra ID
OIDC_2_ICON=EntraID.svg
OIDC_2_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0
OIDC_2_CLIENT_ID=<app-client-id>
OIDC_2_CLIENT_SECRET=<client-secret>
OIDC_2_REDIRECT_URI=http://localhost:8501/0_Login
OIDC_2_POST_LOGOUT_REDIRECT_URI=http://localhost:8501/
OIDC_2_SCOPES="openid profile email offline_access"
OIDC_2_PROMPT=select_account
OIDC_2_STATE_SECRET=<long-random-secret>
```

## Provider Notes

### Keycloak

- Typical issuer format: `http(s)://<host>/realms/<realm>`
- Redirect URI in the Keycloak client must exactly match `OIDC_<n>_REDIRECT_URI`.
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

Reporter stores the authentication source in `session.auth_source`. Current values are `local` or provider-qualified OIDC values such as `oidc:1` or `oidc:2`. This field is used to determine OIDC session restore, refresh, and logout behavior.

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
- the provider is enabled (`OIDC_<n>_ENABLED=true`)

### `invalid_grant` or `Code not valid`

Check:

- redirect URI exact match between IdP client config and `OIDC_<n>_REDIRECT_URI`
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
