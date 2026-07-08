# UI Bootstrapping

This document describes the startup wiring for the UI process before normal page interactions begin.

## Startup Path

UI startup is driven by `bin/serve_ui`:

1. Run `ui.bootstrap.main()` (Python one-shot bootstrap phase).
2. Change working directory to `apps/python/ui/`.
3. Start Streamlit with `streamlit run app.py` (from that directory).

This split is important: database/bootstrap sync runs before Streamlit serves requests.

## What Bootstrap Does

`apps/python/ui/bootstrap.py` performs:

1. `init_databases()`
   - initializes DB layer and migrations needed by runtime
2. `sync_reports_from_config()`
   - synchronizes report metadata from `apps/python/reports/config.toml`
   - prunes stale/orphan mappings
3. `sync_admin_group()`
   - ensures `admin` user group exists
   - ensures admin group has report mappings
4. `sync_default_oidc_group()`
   - ensures non-privileged default OIDC group (`viewer`) exists
5. `sync_admin_user()`
   - ensures bootstrap `admin` account exists (unknown random password hash)
   - set a login password with `bin/admin_passwd` in development, or
     `docker exec -it reporter-ui /opt/reporter/bin/admin_passwd` in production
     (see [Quick Start](../QUICK_START.md) and [standalone](../../operations/install/STANDALONE.md) /
     [distributed](../../operations/install/DISTRIBUTED.md) install guides)

## Why It Matters

Without bootstrap synchronization:

- report lists and report-group mappings in admin DB can drift from `apps/python/reports/config.toml`,
- required default groups/users may be missing,
- admin pages and UI access checks can fail or behave inconsistently.

## Config Touch Points

Primary files to inspect when changing startup behavior:

- `bin/serve_ui`
- `apps/python/ui/bootstrap.py`
- `apps/python/ui/db/init/report_sync.py`
- `apps/python/ui/db/init/admin_sync.py`

## Report Config Source

UI runtime and bootstrap both depend on combined report config:

- `apps/python/reports/config.toml` (generated from report TOML files)

If you add/remove reports, ensure combined config (run `task combine-configs`) is regenerated before validating UI behavior.

## Operational Dependencies

Bootstrap and runtime depend on:

- admin/data DB environment variables,
- UI session variables (for example `UI_JWT_EXPIRATION_MINUTES`),
- OIDC variables when OIDC providers are enabled.

See:

- [Environment Variables](../../operations/ENVIRONMENT_VARIABLES.md)
- [UI Operational Guide](../../operations/UI_ADMIN_GUIDE.md)

## Minimal Mental Model

```text
bin/serve_ui
  -> ui.bootstrap.main()
      -> init_databases()
      -> sync report metadata + default groups/users
  -> streamlit run apps/python/ui/app.py
```

## Links

- Next: [UI pages and navigation](ui_pages_navigation.md)
- [Back to development guide](../DEVELOPMENT_GUIDE.md)
