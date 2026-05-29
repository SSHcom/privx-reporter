# Sync Server Bootstrapping

This document describes the minimal wiring needed to understand and extend sync server execution.

## Startup mental model

Sync server startup has following stages:

1. **Enter sync runtime** through `sync_server/main.py` (`main()`).
2. **Load config** from environment with `SyncConfig` (`lib/env_sync.py`).
3. **Initialize databases** with `init_databases()` (connections, migrations, bootstrap tasks).
4. **Create PrivX client** with `get_privx_client()`.
5. **Start schedulers**:
   - background thread for `concurrent` stats snapshots (60-second loop)
   - main source loop (5-second tick) for configured sources

If one source sync fails during a loop iteration, the server logs the error and continues future cycles.

## Scheduling model

- `audit` and `connection`:
  - interval-driven using per-source `minutes` config
  - sync calls route through `lib/database/sync/__init__.py`
- `trends`:
  - daily sync based on `SYNC_TREND_HOUR` (UTC)
- `concurrent`:
  - source name for concurrent usage stats (active sessions/connections)
  - dedicated background thread, fixed 60-second interval

## Configuration touch points

When adding or changing source behavior, these are the first files to inspect:

- `lib/env_sync.py`
  - source name constants
  - env parsing and validation
- `sync_server/main.py`
  - source allowlist validation
  - per-source scheduling and dispatch branches

## Before-coding checklist for any new source

Use this checklist before implementing:

1. Define source behavior:
   - time-series (high-volume, windowed manager path), or
   - non-time-series (standalone path).
2. Add a table model under `lib/database/models/sync/`.
3. Add a migration under `administration/migration/_files/`.
4. Implement source sync logic under `lib/database/sync/`.
5. Add source constants/config parsing in `lib/env_sync.py`.
6. Register source in `sync_server/main.py` allowlist and scheduler path.
7. Add tests in sync server + source-level test locations.
8. Update development and operations docs.

## Minimal wiring sketch

```text
1. env_sync.py
  -> define source name + config parsing

2. sync_server/main.py
  -> validate source
  -> schedule source
  -> call source sync function
```

## Links

- Next: [Sync source guide (non-time-series)](sync_source_non_time_series.md)
- [Back to development guide](../DEVELOPMENT_GUIDE.md)
