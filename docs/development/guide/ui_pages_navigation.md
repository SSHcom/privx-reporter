# UI Pages and Navigation

This document describes page-level flow and sidebar navigation patterns in the UI.

## Page Discovery and Layout

Streamlit page discovery is flat under `apps/python/ui/pages/`.

Current conventions:

- numbered user pages (`_0_Login.py`, `_1_Home.py`, `_2_Reports.py`, `_3_Report_Files.py`)
- admin pages (`Admin_*.py`) in the same directory

Because page discovery is flat, heavier view logic is moved to `apps/python/ui/views/` and reusable blocks to `apps/python/ui/components/`.

**Note**: A nested page structure is not supported by Streamlit.

## App-Level Routing

`apps/python/ui/app.py` is the initial router:

1. configure logging and page config,
2. initialize session state,
3. redirect:
   - authenticated -> `pages/_1_Home.py`
   - unauthenticated -> `pages/_0_Login.py`

This keeps authentication entry behavior centralized.

## Shared Page Bootstrap

Most pages call `setup_page(...)` from `apps/python/ui/services/page_bootstrap.py`.

`setup_page` handles:

- page config and common style,
- session state initialization,
- session manager init and restore,
- optional auth enforcement (`require_auth`),
- optional sidebar rendering.

Use this as the default page initialization pattern.

## Login Page Special Case

`pages/_0_Login.py` has a callback-specific branch:

- If OIDC callback params are present, it uses `_setup_callback_page()` and calls `complete_oidc_login()` immediately.
- This avoids normal `setup_page()` side effects during callback processing.

Normal login rendering still uses `setup_page()`.

## Sidebar Navigation Model

Sidebar rendering lives in `apps/python/ui/components/sidebar.py`.

Main sections:

- report navigation tree
- report files shortcut
- admin section (admin users only)
- account/profile/logout actions

Report selection writes `selected_primary` and `selected_subcommand` into session state, then routes to `pages/_2_Reports.py`.

## Report Views

Sidebar report views are resolved by `apps/python/ui/services/report_view_resolver.py`:

1. Build default grouped view from `apps/python/reports/config.toml`.
2. Filter by user-visible reports (unless admin).
3. Optionally append alternate report-group views from admin DB.
4. Cache resolved views in session state.

This allows user-facing navigation grouping without changing report permission rules.

## Reports Page Navigation Contract

`pages/_2_Reports.py` resolves selected report target from:

1. session state (`selected_primary`, `selected_subcommand`)
2. URL query params as fallback (`primary`, `subcommand`)

It enforces access (`can_access_report`) before rendering form and output blocks.

## Files Page Navigation Contract

`pages/_3_Report_Files.py` renders report files:

- admin users: all group/user directories
- non-admin users: their own scoped directory

It still enforces per-report access before allowing file actions.

## Dashboard Scope Note

Admin dashboard internals are intentionally not documented in depth here because dashboard data-fetching structure is expected to change in the near term.

## Links

- Next: [UI report execution](ui_report_execution.md)
- [Back to development guide](../DEVELOPMENT_GUIDE.md)
