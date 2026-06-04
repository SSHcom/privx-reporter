# Sync Deterministic Record IDs

This document explains how to design deterministic `record_id` values for time-series sync rows.

Deterministic IDs are required for idempotent inserts with `(timestamp, record_id)` and `ON CONFLICT DO NOTHING`.

## Why this matters

Time-series sync intentionally overlaps boundaries (latest timestamp can be fetched again). If IDs are deterministic, overlap re-fetches are safe and duplicates are ignored by the database.

If IDs are unstable, the same source row can get different IDs and be inserted multiple times.

## ID strategy options

Choose the simplest strategy that remains stable and unique enough for your source.

### 1) Timestamp-only (rare)

Sometimes a timestamp alone is enough, but only when the source guarantees one logical record per timestamp.

Use this carefully. Same-timestamp events are uncommon but can still happen in real systems.

### 2) Composite ID (preferred when available)

Build ID from stable fields that together identify the source record.

Example from connections:

- `connection_id|connected_timestamp`

This is implemented in `apps/python/lib/database/sync/time_series/sources/connection.py`.

Composite IDs are usually readable, efficient, and easy to reason about.

### 3) Hash of canonical payload (fallback when fields are weak)

When there is no reliable field combination, hash the full canonicalized payload.

Example from audit events:

- canonical JSON (sorted keys, stable separators) -> SHA-256

This is implemented in `apps/python/lib/database/sync/time_series/sources/audit.py`.

This strategy is robust, but make sure canonicalization is stable so equivalent payloads always produce the same hash.

## Same-timestamp collision risk

Potential issue: multiple distinct records can share the same timestamp.

Guideline:

- never rely on timestamp-only unless source behavior guarantees uniqueness
- prefer composite IDs with a stable primary key + timestamp when possible
- use canonical payload hash when no good natural key exists

## Practical checklist

When implementing `<sync source>.build_record_id(...)`:

1. Verify ID output is deterministic across repeated sync runs.
2. Verify the same source record always yields the same ID.
3. Verify different source records in the same timestamp bucket still get different IDs.
4. Verify fallback behavior when required fields are missing (`None` -> row skipped).

## Related references

- `apps/python/lib/database/sync/time_series/sources/audit.py`
- `apps/python/lib/database/sync/time_series/sources/connection.py`
- `docs/development/guide/sync_source_time_series.md`

## Links

- Next: [Sync server miscellaneous guidance](sync_server_misc_guidance.md)
- [Back to development guide](../DEVELOPMENT_GUIDE.md)
