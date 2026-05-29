# Environment Variables

This document describes environment variables used by PrivX Reporter components.
Values shown are examples only.

## Database Variables

Database variables configure connections to two instances:
- Data DB (TimescaleDB) for synchronized report data
- Admin DB (PostgreSQL) for administration and UI metadata

### Data Database (PostgreSQL with TimescaleDB)

| Variable           | Example       | Purpose                                                          |
| ------------------ | ------------- | ---------------------------------------------------------------- |
| `DB_DATA_HOST`     | `localhost`   | Data DB host name                                                |
| `DB_DATA_PORT`     | `5444`        | Data DB port (external/host-mapped port in containerized setups) |
| `DB_DATA_NAME`     | `report_data` | Data DB database name                                            |
| `DB_DATA_USER`     | `postgres`    | Data DB user name                                                |
| `DB_DATA_PASSWORD` | `postgres`    | Data DB password                                                 |
| `DB_DATA_SSL_MODE` | `on`          | Data DB SSL mode (`on` or `off`)                                 |

### Admin Database (PostgreSQL)

| Variable            | Example        | Purpose                                                           |
| ------------------- | -------------- | ----------------------------------------------------------------- |
| `DB_ADMIN_HOST`     | `localhost`    | Admin DB host name                                                |
| `DB_ADMIN_PORT`     | `5445`         | Admin DB port (external/host-mapped port in containerized setups) |
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

UI variables control temporary admin credentials and session lifetimes.

| Variable                    | Example       | Purpose                                                     |
| --------------------------- | ------------- | ----------------------------------------------------------- |
| `UI_TMP_ADMIN_PASSWORD`     | `uuid-string` | Temporary initial admin password                            |
| `UI_JWT_EXPIRATION_MINUTES` | `60`          | JWT expiration time in minutes                              |
| `UI_COOKIE_MAX_AGE_MINUTES` | `1440`        | Session cookie max age in minutes                           |
| `UI_ENABLE_SESSION_DEBUG`   | `false`       | Enables Session Debug panel in own profile view (all users) |

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

### Auth Mode

| Variable       | Example                | Purpose                                                                             |
| -------------- | ---------------------- | ----------------------------------------------------------------------------------- |
| `UI_AUTH_MODE` | `local,keycloak,entra` | Comma-separated list of auth modes; `local` enables password login, others are OIDC |

### Per-Provider Variables

Provider variables are prefixed with the provider id in uppercase (e.g., `KEYCLOAK_OIDC_*`, `ENTRA_OIDC_*`).

| Variable                                   | Example                                 | Purpose                                                                              |
| ------------------------------------------ | --------------------------------------- | ------------------------------------------------------------------------------------ |
| `<provider>_OIDC_ISSUER`                   | `http://localhost:8080/realms/reporter` | OIDC issuer URL                                                                      |
| `<provider>_OIDC_CLIENT_ID`                | `reporter-local`                        | OIDC client ID                                                                       |
| `<provider>_OIDC_CLIENT_SECRET`            | `<client-secret>`                       | OIDC client secret                                                                   |
| `<provider>_OIDC_REDIRECT_URI`             | `http://localhost:8501/0_Login`         | Redirect URI for auth callback (must match IdP config exactly)                       |
| `<provider>_OIDC_POST_LOGOUT_REDIRECT_URI` | `http://localhost:8501/`                | Post-logout redirect URI                                                             |
| `<provider>_OIDC_STATE_SECRET`             | `<long-random-secret>`                  | Secret for signing OIDC `state` parameter (CSRF protection)                          |
| `<provider>_OIDC_SCOPES`                   | `openid profile email`                  | OIDC scopes (default: `openid profile email`)                                        |
| `<provider>_OIDC_PROMPT`                   | `login`                                 | OIDC `prompt` parameter (default: `login`; use `select_account` for Entra if needed) |

### Optional Global Variables

These variables are not provider-prefixed and apply globally across all OIDC providers. They control optional features for user auto-provisioning and group mapping.

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
