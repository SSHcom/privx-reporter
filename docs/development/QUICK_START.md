# PrivX Reporter - Quick Start

This guide explains how to run the Reporter components locally.

Before you start, make sure the prerequisites mentioned in the development [README](./README.md) are covered.

### Related documentation

- [Admin Guide](../operations/CLI_ADMIN_GUIDE.md) - manage synced events, database migration
- Other [Operations](../operations/) documents

## 1) Verify that CLI scripts will run

Simple tests to see that the `report` and `admin` commands are runnable.

- Run `bin/report -h` to see available report groups.
- Run `bin/report <group> <command> -h` to see report options in a group.
- Run `bin/admin -h` to see available administration command groups.
- Run `bin/admin <group> <command> -h` to see administration options in a group.

For administration command usage and conventions, see [Administration Operational Guide](../operations/CLI_ADMIN_GUIDE.md).

## 2) Prepare environment variables

- Copy `.env-example` to `.env`.
- If you already have a `.env` file, ensure it is up to date with `.env-example`.
- Update `.env`:
  - Log in to the PrivX instance you want to connect to, then find `PRIVX_API_*` values in `Administration -> Deployment -> Integrate with PrivX Using API Clients -> <Client>`.
  - If you want to use a TLS trust anchor, set `PRIVX_CA_CERT`. Otherwise, remove it from `.env`.
  - Leave other values as-is for now.

## 3) Start local databases

The reporter operates with two PostgreSQL databases:

1. **Data database**: historical records synced from PrivX (TimescaleDB extension enabled).
2. **Admin database**: Sync Server and UI configuration data (for example, user groups and users).

### SSL setup (recommended)

For local development, SSL is optional but recommended (You will have less trouble if you leave it on).

If you want to disable SSL, set these in `.env`:

```
DB_DATA_SSL_MODE=off
DB_ADMIN_SSL_MODE=off
```

Extract certificate files:
- `tar -xvzf dev-pg-ssl.tar.gz`
- Verify that `.dev-pg-ssl` contains: `pg_hba.conf`, `server.crt`, `server.key`
- `pg_hba.conf` defines PostgreSQL client authentication rules. In this setup, it enforces SSL connections.

### Start database containers

**Note**: On some systems you have to use `docker compose` instead of `docker-compose`.

- Start containers:
  - `docker-compose -f docker-compose-db.yml up`
- To run in background:
  - `docker-compose -f docker-compose-db.yml up -d`
- To check logs:
  - `docker logs reporter-dev-admin-db`
  - `docker logs reporter-dev-data-db`

### Reset database volumes (if needed)

On first run, the databases are initialized and `/usr/local/bin/dev_entry_point.sh` is executed (mapped from local `release/common/pg_ssl_entry_point.sh`).

**If startup fails** due to bad settings or if you need a clean state, reset containers and volumes. This removes synced data and admin configuration.

- Stop containers:
  - `docker-compose -f docker-compose-db.yml stop`
- Remove containers and attached volumes:
  - `docker-compose -f docker-compose-db.yml rm -f -v`
- Start again:
  - `docker-compose -f docker-compose-db.yml up`

## 4) Start the sync server

- Optionally adjust sync environment variables (next section).
- Run: `bin/serve_sync`
- If syncing finds no records:
  - Temporarily increase interval/range values.
  - Restart sync.
  - Restore defaults and restart again.

### Sync environment variables

Default values in `.env-example` are usually fine for development.

- `SYNC_BATCH_SIZE`: Number of records requested per PrivX API call. For large datasets (for example, 100k+), avoid setting this too low.
- `SYNC_MAX_RANGE_HOURS`: Maximum sync range; overrides calculated date range.
  - Mainly useful if the server has been down for a longer time and you don't want to sync everything from that period.
- `SYNC_CONNECTION`: Connection sync behavior as `<interval>,<initial sync range>,<retention days>`.
  - The initial sync range applies only on first run. After that, the latest sync timestamp defines the opening time.
- `SYNC_AUDIT`: Audit event sync behavior (same as for `SYNC_CONNECTION`).

## 5) Verify that reports can be generated

Run a few reports to test if we can connect to both PrivX and the database.

### Verify reports using PrivX API
- Get hosts created in PrivX:
  - `bin/report list hosts`

- Get roles created in PrivX:
  - `bin/report list roles`

### Verify reports using the database (filled by sync server)

- Query event code `802 - host modified` events:
  - `bin/report events query --event-id 802`

- List unique events currently synced to the database:
  - `bin/report list events`

## 6) Start the UI

- Run: `bin/serve_ui`
- Open `http://localhost:8501` in the browser

On a fresh admin database, bootstrap creates an `admin` user with a random password hash that is not stored. Before the first login, set a known password (with the UI and admin database running and `.env` database settings correct):

```sh
bin/admin_passwd
```

Sign in as `admin` with the password you set.

### UI usage notes

- The UI covers most CLI reporting use cases (except printing directly to `STDOUT`).
- Some reports include a "Report to page" option. High-volume reports (for example, events) may not.
- Creating a report always generates a report file.
- Report files can be deleted from each report page or from the "Report Files" page.