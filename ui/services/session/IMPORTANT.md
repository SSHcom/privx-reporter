# Session State Management (Important)

**Note**: Unless stated otherwise, referenced files are located in `ui/services/session`

## Core Flow

1. `ui/services/page_bootstrap.py -> setup_page()` calls:
   - `init_session_state()`
   - `session_manager.init()`
   - `session_manager.restore_session()`
   - `require_auth()` (for protected pages)
2. Auth/session state lives in `st.session_state` via `keys.py`.
3. Persistent session identity lives in:
   - browser cookie (`ui_session_token`)
   - DB session row (`session` table, keyed by token, with `updated` timestamp)

## Modules

- `keys.py`: canonical `st.session_state` keys.
- `state.py`: initialize/hydrate/clear auth state + auth guard.
- `cookie_store.py`: cookie read/write/delete and cookie max-age handling.
- `lifecycle.py`: JWT expiration and extension time calculations.
- `session_manager.py`: orchestration across cookie, DB, and app state.

## Cookie Read vs Write

- **Reading** uses `st.context.cookies` (synchronous, parsed from HTTP request
  headers). This means the session token is available on the very first script
  run after a full page reload — no iframe round-trip required.
- **Writing/deleting** uses the iframe-based `CookieManager` component because
  `st.context.cookies` is read-only.
- After login, the cookie-set iframe writes `document.cookie` in JS, but this
  value won't appear in `st.context.cookies` until the next full HTTP request.
  `session_manager` therefore keeps an in-memory fallback path so auth does not
  break while cookie visibility lags.

## Login Flow

1. `_0_Login.py` validates credentials, calls `hydrate_authenticated_state()`
   and `session_manager.start_session()`.
2. `start_session()` creates the DB session, writes the cookie via the iframe
   component, stores the token in `session_state`, and opens a grace window.
3. Login immediately calls `st.switch_page("pages/_1_Home.py")` — it does
   **not** wait for an iframe-triggered rerun.
4. On the Home page, `restore_session()` sees the grace window is active and
   uses the in-memory token (ignoring any stale cookie from `st.context.cookies`).

## Expiration Rules

- Session TTL is based on DB `updated` + `UI_JWT_EXPIRATION_MINUTES`.
- If expired in `restore_session()`: end the specific session via
  `_end_specific_session()`, then re-login required.
- If active but `< 10 min` remaining: touch DB `updated` to extend TTL.

## Token Selection in `restore_session()`

Priority order:
1. **In-memory token exists and cookie mismatches** → use in-memory token and
   rewrite cookie.
2. **In-memory token exists and cookie is missing** → use in-memory token and
   retry cookie write.
3. **Grace window active + in-memory token** → use in-memory token and refresh
   cookie (covers post-login write lag).
4. **Cookie token present** → use cookie token (normal restore path).
5. **Neither** → no session, clear auth state, return False.

Important behavior:
- In-memory token is intentionally preferred while the current Streamlit session
  is active. This avoids false logouts caused by stale/missing `st.context.cookies`.
- DB session lookup and TTL checks are still authoritative; in-memory token alone
  does not bypass DB validation.

## Stale Token Safety

- When a token has no matching DB session, `restore_session()` does **not**
  call `end_session()`. It only clears the cookie and auth state directly.
  This prevents accidentally killing a different valid session that
  `start_session()` may have just stored in `session_state`.
- For expired/invalid DB sessions, `_end_specific_session(token)` ends
  only the exact token passed in, not whatever is in `session_state`.
- `end_session()` (the public API for logout) reads from `session_state`
  first, then falls back to the cookie. It is only called by explicit
  logout actions, never from `restore_session()`.

## Loop-Safety Rules (Streamlit)

- **Do not recreate CookieManager on every rerun.**
  - `cookie_store.init()` reuses one instance via `_CM_KEY` in `st.session_state`.
  - `setup_page()` must not `pop()` `_CM_KEY` per rerun.
- **Do not trigger auth clears on transient post-login cookie race.**
  - `session_manager` uses a short cookie-sync grace window after login.
  - During grace, the in-memory token is always preferred over the cookie.
- Keep `restore_session()` idempotent and side effects minimal.
- Never call `end_session()` from `restore_session()` — use targeted cleanup.

## Environment Inputs

- `UI_JWT_EXPIRATION_MINUTES`: DB session inactivity TTL.
- `UI_COOKIE_MAX_AGE_MINUTES`: browser cookie max-age.

## Change Safety Checklist

- Preserve `ui/services/page_bootstrap.py -> setup_page()` call order.
- Keep one CookieManager instance per Streamlit session state.
- Re-test login, logout, page navigation, and expiry behavior after changes.
- If loops appear, check logs for:
  - `restore_session: no DB session for token=...` followed by
    `end_session token=...` with a **different** token → stale token
    is poisoning restore and nuking the new session.
  - `restore_session: cookie token mismatch cookie=... memory=..., preferring in-memory token`
    indicates stale/missing cookie handling is active.
