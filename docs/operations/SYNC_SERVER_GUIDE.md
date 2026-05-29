# Sync Server Operational Guide

This operational guide explains how the sync server ingests, stores, and protects historical reporting data.

## Runtime Behavior

The sync server pulls historical data from PrivX into the local data database for time-series reporting.

Supported sources:
- System trends (daily, from local sync DB)
- Concurrent session stats (continuous background refresh)
- Audit events
- Connections

On startup, the sync server:
- Loads and validates sync configuration from environment variables.
- Connects to admin and data databases.
- Creates required sync tables if missing.
- Seeds the audit-event allowlist table in admin DB when empty.
- Starts a loop that checks source schedules every 5 seconds.

Loop resilience:
- Each sync cycle is wrapped in exception handling, so unexpected source errors do not terminate the server process.
- On non-interrupt failures, the cycle logs the error and retries on the next loop iteration.

For each due source run, it:
- Uses an effective sync start point (latest local timestamp, or first-run look-back window).
- Splits the full sync range into adaptive time windows (smallest configured size first).
- Fetches each time window from PrivX in offset-paginated API batches.
- Filters out records strictly older than the latest stored timestamp.
- Inserts rows with conflict-safe writes, making retries idempotent.
- On retryable failures, shrinks the current time window and retries with a narrower slice.
- When already at the minimum window size, retries transient PrivX API failures with exponential backoff before aborting the current source cycle.

## Stored Data

Data tables:
- `audit_event`: timestamp, deterministic `record_id`, event metadata, full payload JSON
- `connection`: timestamp, deterministic `record_id`, full payload JSON

Primary key for both:
- `(timestamp, record_id)`

Retention:
- Both tables are Timescale hypertables with retention policies configured from source settings.

## Source-Specific Notes

Audit event sync:
- Syncs only enabled audit event codes from the admin table.
- Also includes `802` principal-modification events when they contain principal account/user/role changes, even if `802` is disabled.
- Builds `record_id` as a SHA-256 hash of the canonical audit payload. We use a hash (instead of relying on `created` alone) because (although very unlikely) different events can share the same timestamp, and the payload hash still gives each event a stable unique ID.
- Normalizes nested `message.modifications` when it is JSON encoded as a string.

Connection sync:
- Uses `connected` timestamp for ordering/filtering.
- Requires both `id` and `connected` to build `record_id`; invalid rows are skipped.
- Does not use `created` for `record_id` because `created` reflects when the record was stored, which can differ from the actual connection event time (`connected`); using `connected` keeps idempotency keys aligned with the sync timestamp source.

## Data Integrity

- Sync windows intentionally overlap so that records near the boundary between runs are never missed.
- Duplicates from the overlap are discarded by conflict-safe inserts on the `(timestamp, record_id)` primary key.
- See [Sync source: time-series](../development/guide/sync_source_time_series.md) and [Sync deterministic record IDs](../development/guide/sync_deterministic_record_ids.md) for details.

## Sync Strategy Tuning

Sync uses two controls at the same time:
- **Time slicing**: split one sync cycle into time windows.
- **API pagination**: fetch each window in pages using offset/limit.

This means one source cycle effectively does:
1. Pick `start_time -> end_time` (latest stored timestamp or first-run look-back, then clamp with `SYNC_MAX_RANGE_HOURS`).
2. Process that range in one window at a time (`SYNC_WINDOW_SIZES_MINUTES` controls possible window sizes).
3. For each window, fetch from PrivX page-by-page (`SYNC_BATCH_SIZE` is the per-request `limit`).
4. Insert rows idempotently; then decide the next window size from the window's `total_count` and `SYNC_MAX_RECORDS_PER_WINDOW`.

### `SYNC_WINDOW_SIZES_MINUTES`

- Comma-separated positive integers (for example `3,4,5,6,7,8,9,10,11,12,13,14,15`).
- The list is sorted and used as the allowed window-size ladder.
- Every cycle starts at the smallest value.
- If a window is "light" (`total_count <= SYNC_MAX_RECORDS_PER_WINDOW`), next window grows to the next size.
- If a window is "heavy" (`total_count > SYNC_MAX_RECORDS_PER_WINDOW`), next window shrinks by `SYNC_WINDOW_SIZE_DOWN_MINUTES`, mapped to the nearest configured size.
- On retryable API errors, the current window is shrunk first; only the minimum size window uses retry-with-backoff logic.

Practical effect: this controls *how much time* each API query covers.

### `SYNC_MAX_RECORDS_PER_WINDOW`

- Positive integer threshold used by adaptive windowing.
- Compared against the first page `total_count` reported for each window.
- Does **not** limit rows written directly; it is a signal that the current time slice is too dense (or safe to grow).

Practical effect: this controls *target record density per time slice* and helps avoid overly large/heavy windows.

### `SYNC_WINDOW_SIZE_DOWN_MINUTES`

- Positive integer down-step size in minutes (default `2`).
- Controls how aggressively windows shrink after a "heavy" window or retryable error.
- The down-step is always mapped onto values from `SYNC_WINDOW_SIZES_MINUTES`, so effective sizes stay on the configured ladder.

Practical effect: this controls *how fast* adaptive windows narrow under load.

### `SYNC_BATCH_SIZE`

- Positive integer passed to PrivX fetch calls as `limit`.
- Also used as the pagination step (`offset += SYNC_BATCH_SIZE`) until a page returns fewer than `SYNC_BATCH_SIZE` items.
- Applied inside each adaptive time window.

Practical effect: this controls *how many records one API request asks for*, independent of window duration.

### How These Four Work Together

- `SYNC_WINDOW_SIZES_MINUTES` decides time coverage per window.
- `SYNC_MAX_RECORDS_PER_WINDOW` decides whether to widen or narrow that coverage for the next window.
- `SYNC_WINDOW_SIZE_DOWN_MINUTES` decides how large each downward adaptation step is.
- `SYNC_BATCH_SIZE` decides request size while paginating inside the current window.

If you increase `SYNC_BATCH_SIZE`, each request gets larger, but window adaptation still depends on `SYNC_MAX_RECORDS_PER_WINDOW`.  
If you increase `SYNC_MAX_RECORDS_PER_WINDOW`, windows are more likely to grow to larger durations from `SYNC_WINDOW_SIZES_MINUTES`.  
If you reduce available window sizes, the sync stays in narrower time slices even when API pages are small.

## `SYNC_MAX_RANGE_HOURS` Clamp

- For both sources, start-time selection first chooses a candidate: latest local timestamp when data exists, otherwise `now - range_minutes` from that source's config (`SYNC_AUDIT` or `SYNC_CONNECTION`).
- `range_minutes` is the second value in `SYNC_AUDIT` / `SYNC_CONNECTION` (`minutes,range_minutes,retention_days`) and defines first-run look-back per source.
- If the candidate start is older than `now - SYNC_MAX_RANGE_HOURS`, it is clamped to that maximum-backfill boundary.
- Practical effect: `SYNC_MAX_RANGE_HOURS` caps both first-run look-back and catch-up after downtime, while overlap/idempotency logic still applies at the effective boundary.

## Environment Variables

Sync-specific scheduling variables include:

- `SYNC_SOURCES`
- `SYNC_BATCH_SIZE`
- `SYNC_WINDOW_SIZES_MINUTES`
- `SYNC_WINDOW_SIZE_DOWN_MINUTES`
- `SYNC_MAX_RECORDS_PER_WINDOW`
- `SYNC_MAX_RANGE_HOURS`
- `SYNC_TREND_HOUR`
- `SYNC_AUDIT`
- `SYNC_CONNECTION`

The full environment variable reference (including database and PrivX API settings required by sync at runtime) is documented in [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md).
