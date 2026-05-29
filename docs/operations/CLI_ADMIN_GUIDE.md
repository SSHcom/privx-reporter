# Administration Operational Guide

The Admin CLI is used for managing configurations and perform various administrative tasks. Currently the following can be managed:

- Database migrations
  - Schema parity test (ensure the schema match what's in the database)
- Audit event sync management (controlling which event codes are enabled for sync processing).

The CLI is using groups and sub-commands to separate managing domains:
```sh
admin <group> <sub-command> [options]
```

#### Note:
Commands in this guide assume Reporter binaries are available in your PATH. If you run directly from a cloned repository, use `bin/admin`, `bin/serve_sync`, and `bin/serve_ui` instead.

# Migration command group

Use this group to manage schema migrations for both databases: `admin` and `data`.

## Apply pending migrations

```sh
admin migration up
```

- Applies all pending migration files from `administration/migration/_files`.
- One migration file may contain SQL for `admin tables`, `data tables`, or both.

**Note:** The sync server and reporter UI automatically applies latest migrations on startup.

## Show migration status

```sh
admin migration status
```

- Shows applied migrations (with target DB and timestamp).
- Shows pending migrations that are not yet applied.

## Roll back migrations

```sh
admin migration down
admin migration down --steps 2
```

- `--steps` default is `1`.
- One step = one migration file.
- If a migration file targets both DBs, one rollback step rolls back both `admin` and `data`.

## Auto-apply behavior

- `serve_sync` runs migrations on startup and applies pending migration changes automatically.
- `serve_ui` runs migrations on startup and applies pending migration changes automatically.
- You can still run `admin migration ...` manually for operational control and troubleshooting.

## Migration file contract

Each migration file in `administration/migration/_files` must define:

- `up() -> dict[str, list[str]]`
- `down() -> dict[str, list[str]]`

In both dicts, the key is the database target (`"admin"` or `"data"`), and the list is the SQL statements to run on that target.

## Database schema parity test

This repository includes a dedicated database test that validates SQLAlchemy table contracts against the live migrated schema:

- Test file: `tests/lib/database/models/test_schema_parity.py`
- Marker: `database`
- Task command: `task test-database`

### What it validates

For every table registered in `admin_db_metadata` and `data_db_metadata`, the test compares model declarations vs reflected DB schema for:

- Column names
- Broad column type family (for example `String` vs `VARCHAR`)
- Nullability
- Primary key column set

The test intentionally focuses on table structure used by application queries and record field access.

### How to run

Start the isolated test database:

```sh
docker compose -f docker-compose-test.yml up -d
```

Run parity checks:

```sh
task test-database
```

### When to run (and why)

Run `task test-database` after any change to:

- Migration SQL (`administration/migration/_files`)
- SQLAlchemy table models (`lib/database/models/`)

Reason: migrations define runtime database structure, while model tables define the query contract used by code. If they drift, failures usually show up later at runtime (missing columns, wrong nullability, type mismatches, broken PK assumptions). The parity test catches this drift immediately in a controlled DB before deployment.

# Sync command group

Use this group to backfill historical data from the PrivX API into the local database.

## Backfill historical data

Backfill audit events and/or connections for a specific time range. This is useful for:
- Populating the database with historical data on initial setup
- Recovering data after downtime
- Filling gaps in the synced data

```sh
admin sync backfill --days 30
admin sync backfill --from 2026-01-01
admin sync backfill --days 7 --source audit
admin sync backfill --from 2026-03-15 --source connection --batch-size 500
```

### Options

- `--days <n>` - Number of days to look back from today
- `--from <YYYY-MM-DD>` - Start date for backfill (syncs from this date until today)
- `--source <audit|connection|all>` - Which data source to backfill (default: all)
- `--batch-size <n>` - Number of records to fetch per API call (default is resolved from `SYNC_BATCH_SIZE`)

**Note:** Either `--days` or `--from` must be provided, but not both.

### Duplicate handling

Backfill operations are idempotent and safe to run on non-empty tables:
- Both `audit_event` and `connection` tables use composite primary keys `(timestamp, record_id)`
- Inserts use `ON CONFLICT DO NOTHING`, so existing records are skipped
- The `record_id` is deterministic (audit: SHA-256 hash of payload, connection: `{id}|{connected}`)

This means you can re-run backfill for overlapping time ranges without creating duplicates.

### Backfill vs sync server

Both use the same sync engine (adaptive time windows + API pagination), but they choose time range differently.

- **Backfill (`admin sync backfill`)**
  - Operator supplies explicit range using `--days` or `--from`.
  - Uses `calculate_backfill_range()` to sync `start_time -> now`.
  - Ignores latest stored timestamp when selecting start; useful for controlled historical loads and gap recovery.
  - Runs once and exits.

- **Sync server**
  - Runs continuously on schedule (`SYNC_AUDIT` / `SYNC_CONNECTION` intervals).
  - Uses latest stored timestamp as start when data exists; otherwise uses source `range_minutes` first-run look-back.
  - Applies `SYNC_MAX_RANGE_HOURS` clamp to cap catch-up depth.
  - Keeps looping and syncing due sources.

Because the underlying strategy is shared, the same tuning knobs affect both:
- `SYNC_WINDOW_SIZES_MINUTES`
- `SYNC_WINDOW_SIZE_DOWN_MINUTES`
- `SYNC_MAX_RECORDS_PER_WINDOW`
- `SYNC_BATCH_SIZE` (unless overridden with `--batch-size` in backfill)

For practical tuning guidance, see [Sync Server Guide - Sync Strategy Tuning](SYNC_SERVER_GUIDE.md#sync-strategy-tuning).

# Event command group

## List events

```sh
admin event list
admin event list --enabled
admin event list --disabled
admin event list --fixed
```

- `--enabled` and `--disabled` are mutually exclusive.
- `--fixed` supersedes both — "fixed" events are permanent sync targets that cannot be disabled.
- Output is tab-separated: `CODE`, `NAME`, `DESCRIPTION`.

## Enable or disable an event code

```sh
admin event enable --code 802
admin event disable --code 802
```

- Returns an error if the code is not found in the admin table.
- Fixed events cannot be enabled or disabled — they are always sync targets.
