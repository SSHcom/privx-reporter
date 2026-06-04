# Sync Source Guide: Time-Series

This guide explains the time-series sync path used by high-volume sources such as `audit` and `connection`.

This is the more advanced sync path in the repository. Follow it when data volume can become large and you need safe incremental sync with adaptive performance behavior.

## Why this path exists

Time-series sources can return very large datasets for broad time ranges. A single large query can be slow, unstable, or expensive.

To address this, the time-series path uses:

- adaptive time windows
- offset pagination
- retry + window shrink behavior for transient failures
- idempotent inserts with deterministic record IDs

## Time-series module map

```text
apps/python/lib/database/sync/time_series/
├── __init__.py
├── manager.py
├── protocol.py
├── helpers.py
├── window.py
└── sources/
    ├── __init__.py
    ├── audit.py
    └── connection.py
```

- `manager.py`
  - Main class: `SyncManager`
  - Main entrypoints: `SyncManager.sync()`, `SyncManager.backfill()`
  - Role: orchestrates range calculation, window loop, pagination, row processing, and DB insert.
- `protocol.py`
  - Main contract: `SyncSource` protocol
  - Main type: `FetchResult`
  - Role: defines what each source must implement (`prepare`, `fetch_batch`, filtering, normalization, ID building).
- `window.py`
  - Main class: `SyncWindow`
  - Role: adaptive window sizing (grow/shrink) and iteration across contiguous time slices.
- `helpers.py`
  - Main functions: `get_latest_timestamp()`, `calculate_time_range()`, `build_timestamped_row()`
  - Role: shared time-range and row-building helpers used by `SyncManager`.
- `sources/audit.py`
  - Main class: `AuditEventSync`
  - Role: concrete `SyncSource` implementation for audit-specific fetch/filter/normalize/record-ID behavior.
- `sources/connection.py`
  - Main class: `ConnectionSync`
  - Role: concrete `SyncSource` implementation for connection-specific fetch and record-ID behavior.
- `sources/__init__.py`
  - Role: exports available source implementations for manager wiring.

## Source contract (what you implement)

Each source implements the `SyncSource` protocol in `apps/python/lib/database/sync/time_series/protocol.py`.

Small contract sketch:

```python
class SyncSource(Protocol):
    def prepare(self, api: object) -> object: ...
    def fetch_batch(self, api: object, start_time: str, end_time: str, offset: int, limit: int) -> FetchResult: ...
    def filter_item(self, item: dict[str, Any], context: object) -> bool: ...
    def normalize_item(self, item: dict[str, Any]) -> None: ...
    def build_record_id(self, item: dict[str, Any]) -> str | None: ...
```

Use `AuditEventSync` and `ConnectionSync` under `apps/python/lib/database/sync/time_series/sources/` as reference implementations.

## How sync windows work (and why)

A **window** is one time slice of the full sync range, for example a 5-minute span.

Instead of querying the full range in one large API call, the sync manager processes one window at a time and pages through that window using `limit=SYNC_BATCH_SIZE`.

For production-facing tuning guidance and runtime behavior details (adaptive window growth/shrink tradeoffs, retry behavior under API instability, and range clamp effects), see [Sync Server Operational Guide](../../operations/SYNC_SERVER_GUIDE.md#sync-strategy-tuning).

### Window-related environment variables

- `SYNC_WINDOW_SIZES_MINUTES`
  - allowed window sizes (in minutes, example: "5,10,15"), sorted and used as the growth/shrink ladder
- `SYNC_WINDOW_SIZE_DOWN_MINUTES`
  - how aggressively window size is reduced after retryable failures or high-volume windows
- `SYNC_MAX_RECORDS_PER_WINDOW`
  - target upper bound for records inside one window
- `SYNC_BATCH_SIZE`
  - page size for each API request inside a window

### How page count and window size interact

For each window:

1. The first request returns the first page of rows plus the total rows for that window (`total_count`).
2. The manager uses `total_count` to decide whether the **next** window should grow or shrink toward `SYNC_MAX_RECORDS_PER_WINDOW`.
3. The current window still continues paging with `offset += SYNC_BATCH_SIZE` until all pages are fetched.

Example:

- If window size is 5 minutes and first page indicates `count=12_000` with `SYNC_BATCH_SIZE=1_000`, about 12 page requests are needed for that window.
- If `SYNC_MAX_RECORDS_PER_WINDOW=10_000`, the manager keeps current processing but shrinks upcoming windows to reduce load.
- If count is comfortably below the threshold, upcoming windows can grow for better throughput.

This is the core balancing mechanism: keep windows large enough for efficiency, but small enough to avoid overloaded queries.

## Step-by-step runtime flow

### 1) Entry and manager wiring

- `apps/python/sync_server/main.py` schedules source sync based on source config.
- Calls route through `apps/python/lib/database/sync/__init__.py`.
- That module keeps one manager instance per source:
  - `SyncManager(AuditEventSync())`
  - `SyncManager(ConnectionSync())`

### 2) Determine sync range

For regular sync (`SyncManager.sync`):

- reads latest local timestamp (`get_latest_timestamp`)
- computes `(start_time, end_time)` via `calculate_time_range`
- uses `range_minutes` only when no local data exists yet
- optionally clamps range using `max_range_hours`

For backfill (`SyncManager.backfill`):

- caller provides explicit `start_time` and `end_time`
- no “older-than-latest” filtering is applied in this path

### 3) Prepare source context

`context = <sync source>.prepare(api)` runs once before looping windows.

Example:

- `AuditEventSync` loads enabled audit event IDs from admin DB.
- `ConnectionSync` returns no context.

### 4) Process adaptive windows

`SyncWindow` walks through the selected time range in contiguous sub-windows.

- starts from smallest configured window size
- can grow when volume is low
- shrinks when volume is high or retryable errors occur

This keeps requests appropriately sized across different data densities.

### 5) Paginate each window

Inside each window:

- `<sync source>.fetch_batch(..., offset, limit)` is called repeatedly
- offset advances by `batch_size`
- loop stops when API returns short page (`count < batch_size`) or no records

### 6) Transform and filter batch rows

For each fetched item:

1. apply `<sync source>.filter_item(items, context)` (See step 3 for how we get `context`)
2. run `<sync source>.normalize_item`
3. build timestamped row (drop rows older than latest timestamp in incremental path)
4. Use `<sync source>.build_record_id` to build deterministic `record_id`
5. attach source-specific extra fields (optional)

For record ID strategy choices and pitfalls (timestamp-only, composite IDs, canonical payload hash), see [Sync deterministic record IDs](sync_deterministic_record_ids.md).

### 7) Insert idempotently

Rows are inserted with `ON CONFLICT DO NOTHING`.

The table key `(timestamp, record_id)` plus deterministic `record_id` keeps repeated overlap fetches safe and idempotent.

## Data integrity model (important)

This is the main integrity model to preserve when adding sources:

1. Incremental sync starts at the latest stored timestamp (overlap-safe boundary).
2. Rows strictly older than that timestamp are filtered before insert.
3. Duplicate boundary rows are neutralized by primary key + `ON CONFLICT DO NOTHING`.

Result: rerunning overlapping windows does not corrupt data and does not miss same-timestamp boundary records.

## Step-by-step: add a new time-series source

1. **Create data model** in `apps/python/lib/database/models/sync/<source>.py`.
   - Use primary key shape compatible with this path: `timestamp` + `record_id`.
2. **Add migration** in `apps/python/administration/migration/_files/`.
3. **Implement source** in `apps/python/lib/database/sync/time_series/sources/<source>.py`.
   - implement full `SyncSource` contract
   - ensure `build_record_id` is stable and deterministic
4. **Expose source** in time-series source exports (`sources/__init__.py` if needed).
5. **Wire manager wrappers** in `apps/python/lib/database/sync/__init__.py`.
   - add manager instance
   - add `sync_<source>` and optional `backfill_<source>` wrappers
6. **Add env/source registration** in `apps/python/lib/env_sync.py`.
7. **Register scheduling path** in `apps/python/sync_server/main.py`.
   - source allowlist
   - interval tracking and dispatch branch
8. **Add tests**:
   - source behavior tests under `tests/python/lib/database/sync/sources/`
   - manager/server integration behavior where relevant
9. **Update docs**:
   - development guide index and any operations env/runtime docs

## Pitfalls

- Using non-deterministic `record_id` values (breaks idempotency).
- Treating non-time-series snapshot sources as time-series without need.

## Links

- Next: [Sync deterministic record IDs](sync_deterministic_record_ids.md)
- [Back to development guide](../DEVELOPMENT_GUIDE.md)
