# Known Issues

This document tracks known issues and limitations in the reporter-privx application.

## 1. PrivX API "search_roles" request returns incomplete data

**File**: `lib/report_api/roles.py`

### Output Difference between `get_roles` and `roles_search`

- **`get_roles`:** includes validity, timezone, IP masks, start/end times, group_id, etc
- **`search_roles`:** Only basic fields like `name` and `id` are populated

### Impact

- When `roles all` is used with the `--role-name` filter, we do not use `search_roles` as preferred, but instead call `get_roles` and apply post-filters.

## 2. PrivX API "search_connections" doesn't seem to support tags and user_roles filtering

**File**: `reports/connections/query/report.py`

### Issue Description

The PrivX API's `search_connections` endpoint accepts `tags` and `user_roles` parameters as documented in the API specification, but these filters don't work correctly:

- **`tags`**: Always returns 0 results regardless of whether tags exist in connection data
- **`user_roles`**: Always returns all 61 connections regardless of filter value (even non-existing roles)

## 3. UI - Streamlit 404 Errors

### Issue Description

When navigating to any page in the multipage app, the browser console shows 404 errors:

```
GET http://localhost:8501/0_Login/_stcore/health 404 (Not Found)
GET http://localhost:8501/0_Login/_stcore/host-config 404 (Not Found)
```

The Streamlit frontend constructs `_stcore/*` URLs relative to the current page path instead of the app root. The correct URLs should be `/_stcore/health` and `/_stcore/host-config` at the root, but multipage routing prepends the page name.

### Impact

Cosmetic only — the app recovers by falling back to the correct root path. No functional impact.

### Status

Known upstream Streamlit bug tracked in [#7074](https://github.com/streamlit/streamlit/issues/7074) and [#12513](https://github.com/streamlit/streamlit/issues/12513). Remains unfixed as of Streamlit 1.55.0.

## 4. UI - Browser warning

### Issue Description

The browser console shows the warning:

> An iframe which has both allow-scripts and allow-same-origin for its sandbox attribute can escape its sandboxing.

### Why we cannot fix this

Streamlit relies on iframes with both `allow-scripts` and `allow-same-origin` for its components to function. Removing either flag would break the application:

- **`allow-scripts`**: Required for Streamlit components to execute JavaScript.
- **`allow-same-origin`**: Required for the iframe to communicate with the parent Streamlit app (session state, callbacks, etc.).

### Impact

This is a browser security warning, not an error. It signals that the sandboxing is weaker than it could be, but Streamlit's architecture requires this combination to work correctly.

## 5. UI - Cookie value in `st.context.cookies` can lag behind browser state

### Issue Description

In active Streamlit sessions, `st.context.cookies` can temporarily show a stale or missing `ui_session_token` after login/logout because it reflects request-context cookies, not always the latest browser-side write timing.

### Impact

- May cause repeated stale-cookie reads during reruns.
- Can lead to false logout behavior if app logic trusts cookie state alone.

### Current Handling

`session_manager.restore_session()` prefers the in-memory session token (`st.session_state`) when it exists, and still validates the token against DB session/TTL. This avoids false logouts while preserving server-side session security checks.
