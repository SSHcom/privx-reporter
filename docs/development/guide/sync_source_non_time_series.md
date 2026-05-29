# Sync Source Guide: Non-Time-Series

This guide explains how to add sync sources that do **not** use the time-series `SyncManager` flow.

In this repository, current examples are:

- `trends` (`lib/database/sync/trend.py`)
- `concurrent` (`lib/database/sync/concurrent.py`)

`concurrent` is the source name for **concurrent usage statistics** (active sessions and active connections). It is a data category, not a sync algorithm type.

## When this path is the right fit

Use the non-time-series path when your source behaves like periodic snapshots or daily aggregates, not high-volume event streams.

Typical indicators:

- One row per interval/day is enough.
- Data is naturally stored as JSON payload snapshots.
- You do not need adaptive time windows + paginated historical traversal.

## Existing reference patterns

- `concurrent` pattern:
  - fetch active-session and active-connection snapshot counts
  - write one minute-truncated row
  - upsert on `timestamp`
- `trends` pattern:
  - fill missing past-day placeholders
  - insert today's row if missing
  - daily scheduling at configured UTC hour

## Step-by-step: add a new non-time-series source

Before starting implementation:

- This project stores sync data in PostgreSQL with the TimescaleDB extension.
- If you are new to TimescaleDB, read the basics first (hypertables, retention, indexing).
- Review existing migrations in `administration/migration/_files/` to see the established pattern for creating sync tables and applying TimescaleDB-specific setup.

1. **Create table model** in `lib/database/models/sync/`.
   - For this path, the common shape is:
     - `timestamp` as primary key
     - `data` JSONB payload
2. **Create migration** in `administration/migration/_files/`.
   - Create table, add indexes if needed, and define retention policy if required.
3. **Implement sync module** in `lib/database/sync/`.
   - Build one public sync function (for example `sync_my_source(api)`).
   - Fetch PrivX data and normalize to one payload shape.
   - Insert/upsert into the data database.
4. **Define source constant/config** in `lib/env_sync.py`.
   - Add `<source>_SOURCE` name constant used by `SYNC_SOURCES`.
   - Add extra env variables only when source scheduling needs them.
5. **Register source in server loop** in `sync_server/main.py`.
   - Add source to supported-source validation.
   - Add source scheduling branch (thread, interval, or daily gate).
6. **Add tests** for scheduling and sync logic.
7. **Update docs** (`DEVELOPMENT_GUIDE.md`, operations docs, etc if env/runtime changed).

## Minimal registration example

Small example from source validation in `sync_server/main.py`:

```python
if source not in (
    TREND_SOURCE,
    AUDIT_EVENT_SOURCE,
    CONNECTION_SOURCE,
    CONCURRENT_SOURCE,
):
    raise ValueError(f"Unsupported sync source configured: {source}")
```

Adding a new source means extending both this validation and the dispatch/scheduling branch.

## Practical guardrails

- Keep payload keys stable over time for UI/report consumers.
- Prefer wrapper usage through `lib/report_api` when adding repeated PrivX call patterns.
- Avoid drifting into time-series complexity; if you need windowing and deep pagination, switch to the time-series path.

## Links

- Next: [Sync source guide (time-series)](sync_source_time_series.md)
- [Back to development guide](../DEVELOPMENT_GUIDE.md)
