# UI High-Level Architecture

This document describes how the UI is structured and how it integrates with shared Reporter components.

It focuses on stable implementation boundaries developers use when adding or changing UI behavior.

## Scope

The UI is a Streamlit application that:

- authenticates users (local and OIDC),
- applies report visibility and data-scope rules from admin DB state,
- executes the same report handlers used by CLI,
- stores output files under user/group scoped directories.

## Runtime Entry and Routing

UI runtime starts with:

1. `bin/serve_ui`
2. `ui.bootstrap.main()` for DB/bootstrap work
3. `streamlit run app.py` from `apps/python/ui/`

`apps/python/ui/app.py` initializes session state and routes users to:

- `pages/_1_Home.py` when authenticated
- `pages/_0_Login.py` otherwise

## Core Directory Map

- `apps/python/ui/app.py`
  - runtime entry router
- `apps/python/ui/pages/`
  - Streamlit page entrypoints
  - page discovery is flat under this directory (nesting is not supported)
- `apps/python/ui/components/`
  - reusable UI rendering units (report forms/results, sidebar, widgets)
- `apps/python/ui/views/`
  - larger view logic that would make page files too heavy
- `apps/python/ui/services/`
  - orchestration and runtime helpers (report execution, session, auth, config, permissions)
- `apps/python/ui/db/`
  - admin DB query and sync modules used by UI/admin pages and bootstrap
- `apps/python/ui/custom/`
  - custom Streamlit component wrappers (cookie handling)

## UI Request Mental Model

```text
user action in Streamlit page
  -> setup_page() initializes session/auth context
  -> page/service validates access
  -> report_service or admin db query executes logic
  -> page renders result and updates session state
```

## Report Execution Boundary

UI report execution is built around `apps/python/ui/services/report_service.py`:

1. Access check (`can_access_report`) based on user-group mappings.
2. Form values mapped into `argparse.Namespace`.
3. Shared engine call: `lib._report.generator.generate(...)`.
4. Output path scoped to `<REPORT_OUT_DIR>/<group>/<username>`.
5. UI reads generated CSV/JSON for display.

This keeps report business logic in `apps/python/reports/` and UI orchestration in `apps/python/ui/`.

## Authorization Boundary

Two separate checks are important:

1. **Report visibility**
   - controlled by admin DB report mappings for a user group
   - enforced in UI before rendering/running a report
2. **Data scope for filtered reports**
   - non-admin runs pass `user_group_id` into `generate(...)`
   - compatible report handlers apply access-group filtering server-side

## Development Conventions

- Keep page files thin; push reusable logic into `services/`, `components/`, or `views/`.
- Use `apps/python/ui/services/page_bootstrap.py` (`setup_page`) for shared page initialization.
- Use session keys from `apps/python/ui/services/session/keys.py`, not ad-hoc literal keys.
- Keep new behavior aligned with existing report/permission/session contracts.

## Dashboard Scope Note

Admin dashboard data-fetching/widget internals are expected to change in the near term (next few months), so this guide set keeps dashboard internals intentionally high level and focuses on stable UI development paths.

## Links

- Next: [UI bootstrapping](ui_bootstrapping.md)
- [Back to development guide](../DEVELOPMENT_GUIDE.md)
