# Environment Variables

This document describes environment variables used by PrivX Reporter components.
Values shown are examples only.

## Configuration Source and Precedence

Reporter reads configuration using `ENV_SOURCE`:

- `ENV_SOURCE=env`: values are read from process environment variables.
- `ENV_SOURCE=db`: values are resolved in this order:
  1. `app_config` value from admin DB
  2. Process environment variable fallback
  3. Code default

Some variables are always read from process environment because they are needed before DB-backed app config can be loaded, or are intentionally env-only:

- `ENV_SOURCE`
- `DB_*`
- `REPORT_OUT_DIR`
- `BACKUP_DIR`

## Database Variables

Database variables configure connections to two instances:
- Data DB (TimescaleDB) for synchronized report data
- Admin DB (PostgreSQL) for administration and UI metadata

### Data Database (PostgreSQL with TimescaleDB)

| Variable           | Example       | Purpose                                                          |
| ------------------ | ------------- | ---------------------------------------------------------------- |
| `DB_DATA_HOST`     | `localhost`   | Data DB host name                                                |
| `DB_DATA_PORT`     | `5454`        | Data DB port (external/host-mapped port in containerized setups) |
| `DB_DATA_NAME`     | `report_data` | Data DB database name                                            |
| `DB_DATA_USER`     | `postgres`    | Data DB user name                                                |
| `DB_DATA_PASSWORD` | `postgres`    | Data DB password                                                 |
| `DB_DATA_SSL_MODE` | `on`          | Data DB SSL mode (`on` or `off`)                                 |

### Admin Database (PostgreSQL)

| Variable            | Example        | Purpose                                                           |
| ------------------- | -------------- | ----------------------------------------------------------------- |
| `DB_ADMIN_HOST`     | `localhost`    | Admin DB host name                                                |
| `DB_ADMIN_PORT`     | `5455`         | Admin DB port (external/host-mapped port in containerized setups) |
| `DB_ADMIN_NAME`     | `report_admin` | Admin DB database name                                            |
| `DB_ADMIN_USER`     | `postgres`     | Admin DB user name                                                |
| `DB_ADMIN_PASSWORD` | `postgres`     | Admin DB password                                                 |
| `DB_ADMIN_SSL_MODE` | `on`           | Admin DB SSL mode (`on` or `off`)                                 |

## Sync Server Variables

The sync server uses database variables and PrivX API variables, plus sync-specific settings below.
(The same sync-strategy settings are also used by the admin backfill command: `bin/admin sync backfill`).

### Sync Scheduling

| Variable                        | Example                              | Purpose                                                                |
| ------------------------------- | ------------------------------------ | ---------------------------------------------------------------------- |
| `SYNC_SOURCES`                  | `trends,concurrent,connection,audit` | Comma-separated list of sources to sync (processed in listed order)    |
| `SYNC_BATCH_SIZE`               | `1000`                               | Number of records fetched per API call during sync                     |
| `SYNC_WINDOW_SIZES_MINUTES`     | `3,4,5,6,7,8,9,10,11,12,13,14,15`    | Allowed adaptive time-window sizes (minutes) used by the sync strategy |
| `SYNC_WINDOW_SIZE_DOWN_MINUTES` | `2`                                  | Downward shrink step (minutes), mapped onto configured window sizes    |
| `SYNC_MAX_RECORDS_PER_WINDOW`   | `30000`                              | Record-count threshold used to grow/shrink adaptive sync windows       |
| `SYNC_MAX_RANGE_HOURS`          | `2191`                               | Maximum look-back clamp for first run and catch-up                     |
| `SYNC_TREND_HOUR`               | `1`                                  | Optional UTC hour (0-23) to run daily `system_trend` refresh           |

### Per-Source Configuration

Each source uses `interval_minutes,range_minutes,retention_days`:

- **interval_minutes**: how often the source sync runs
- **range_minutes**: first-run look-back window when there is no local data
- **retention_days**: how long source data is retained

| Variable          | Example  | Purpose                                             |
| ----------------- | -------- | --------------------------------------------------- |
| `SYNC_CONNECTION` | `5,7,15` | Connection sync config (`interval,range,retention`) |
| `SYNC_AUDIT`      | `5,7,15` | Audit sync config (`interval,range,retention`)      |

## Reporter Variables

Reporter variables control API fetch size and where report output is written.

| Variable                | Example      | Purpose                                         |
| ----------------------- | ------------ | ----------------------------------------------- |
| `REPORT_API_BATCH_SIZE` | `100`        | Number of records fetched per API call          |
| `REPORT_OUT_DIR`        | `report_out` | Directory where report output files are written |

## UI Variables

UI variables control session lifetimes and related UI behavior. The bootstrap `admin` password is set with `bin/admin_passwd` (development) or `/opt/reporter/bin/admin_passwd` in the UI container (production), not via environment variables.

| Variable                    | Example | Purpose                                                     |
| --------------------------- | ------- | ----------------------------------------------------------- |
| `UI_JWT_EXPIRATION_MINUTES` | `60`    | JWT expiration time in minutes                              |
| `UI_COOKIE_MAX_AGE_MINUTES` | `1440`  | Session cookie max age in minutes                           |
| `UI_ENABLE_SESSION_DEBUG`   | `false` | Enables Session Debug panel in own profile view (all users) |
| `UI_COLLAPSE_LOCAL_LOGIN`   | `false` | Shows local login in a collapsible section below OIDC buttons when at least one OIDC provider is enabled |

## Backup Variables

Backup variables control periodic database dumps by the backup service.

`BACKUP_DIR` is environment-based. `BACKUP_CONFIG` source depends on `ENV_SOURCE`:

- `ENV_SOURCE=env`: set both `BACKUP_DIR` and `BACKUP_CONFIG` in `.env` (all backup config is env-based).
- `ENV_SOURCE=db`: keep `BACKUP_DIR` in `.env`, and manage `BACKUP_CONFIG` in App Config (database-backed settings).

When `ENV_SOURCE=db`, backup starts effectively disabled until `BACKUP_CONFIG` is enabled in App Config. The running service re-checks config every 5 minutes, so backup starts automatically within up to 5 minutes after enabling.

| Variable        | Example              | Purpose                                                       |
| --------------- | -------------------- | ------------------------------------------------------------- |
| `BACKUP_DIR`    | `/opt/reporter/backups` | Directory where DB dump files are written                     |
| `BACKUP_CONFIG` | `true,all,720,5`     | Backup schedule config as `<enabled>,<target>,<interval-minutes>,<snapshots>` |

## PrivX API Variables

PrivX API variables configure connection and authentication for reporter and sync components.

### Connection

| Variable         | Example                          | Purpose                                    |
| ---------------- | -------------------------------- | ------------------------------------------ |
| `PRIVX_HOSTNAME` | `privx-host`                     | PrivX server host name                     |
| `PRIVX_PORT`     | `443`                            | PrivX server port                          |
| `PRIVX_CA_CERT`  | `-----BEGIN CERTIFICATE-----...` | PrivX CA certificate content in PEM format |

### Authentication

| Variable                        | Example          | Purpose             |
| ------------------------------- | ---------------- | ------------------- |
| `PRIVX_API_OAUTH_CLIENT_ID`     | `privx-external` | OAuth client ID     |
| `PRIVX_API_OAUTH_CLIENT_SECRET` | (empty)          | OAuth client secret |
| `PRIVX_API_CLIENT_ID`           | (empty)          | API client ID       |
| `PRIVX_API_CLIENT_SECRET`       | (empty)          | API client secret   |


## OIDC Variables (for UI Authentication)

See [OIDC UI Authentication Guide](OIDC_UI_AUTH_GUIDE.md) for setup instructions and provider-specific notes.

### Provider Enable Flags

Local login is always available. Enable OIDC providers using these settings:

| Variable         | Example | Purpose                        |
| ---------------- | ------- | ------------------------------ |
| `OIDC_1_ENABLED` | `true`  | Enable OIDC provider 1         |
| `OIDC_2_ENABLED` | `false` | Enable OIDC provider 2         |

### Per-Provider Variables

Provider variables use numbered slots (`OIDC_1_*`, `OIDC_2_*`).

| Variable                            | Example                                 | Purpose                                                                              |
| ----------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------ |
| `OIDC_<n>_NAME`                     | `Keycloak`                              | Display name shown on login button                                                   |
| `OIDC_<n>_ICON`                     | `Keycloak.svg`                          | SVG icon file for login button (from `apps/python/ui/assets/icons/oidc/`)            |
| `OIDC_<n>_ISSUER`                   | `http://localhost:8080/realms/reporter` | OIDC issuer URL                                                                      |
| `OIDC_<n>_CLIENT_ID`                | `reporter-local`                        | OIDC client ID                                                                       |
| `OIDC_<n>_CLIENT_SECRET`            | `<client-secret>`                       | OIDC client secret                                                                   |
| `OIDC_<n>_REDIRECT_URI`             | `http://localhost:8501/0_Login`         | Redirect URI for auth callback (must match IdP config exactly)                       |
| `OIDC_<n>_POST_LOGOUT_REDIRECT_URI` | `http://localhost:8501/`                | Post-logout redirect URI                                                             |
| `OIDC_<n>_STATE_SECRET`             | `<long-random-secret>`                  | Secret for signing OIDC `state` parameter (CSRF protection)                          |
| `OIDC_<n>_SCOPES`                   | `openid profile email`                  | OIDC scopes (default: `openid profile email`)                                        |
| `OIDC_<n>_PROMPT`                   | `login`                                 | OIDC `prompt` parameter (default: `login`; use `select_account` for Entra if needed) |

### Optional Global Variables

These variables are not provider-prefixed and apply globally across all OIDC providers. They control optional features for user auto-provisioning and group mapping. If you do not use these features, leave these variables unset.

#### Auto-Provisioning

| Variable                                    | Example                   | Purpose                                                                                      |
| ------------------------------------------- | ------------------------- | -------------------------------------------------------------------------------------------- |
| `OIDC_AUTO_PROVISION`                       | `true`                    | Enable auto-provisioning of local users after IdP login                                      |
| `OIDC_AUTO_PROVISION_DEFAULT_ROLE`          | `viewer`                  | Default user group for auto-provisioned users (not `admin` or `superadmin`)                  |
| `OIDC_AUTO_PROVISION_REQUIRE_EMAIL`         | `false`                   | Require email claim for auto-provisioning (default: `true` when unset)                       |
| `OIDC_AUTO_PROVISION_ALLOWED_EMAIL_DOMAINS` | `example.com,example.org` | Allowed email domains (empty = allow all; requires `OIDC_AUTO_PROVISION_REQUIRE_EMAIL=true`) |

#### Group Claim Mapping

| Variable             | Example                                         | Purpose                                            |
| -------------------- | ----------------------------------------------- | -------------------------------------------------- |
| `OIDC_GROUP_CLAIM`   | `groups`                                        | Claim path for IdP groups (default: `groups`)      |
| `OIDC_GROUP_MAPPING` | `'{"idp-admin":"admin","idp-viewer":"viewer"}'` | JSON mapping of IdP groups to Reporter user groups |
