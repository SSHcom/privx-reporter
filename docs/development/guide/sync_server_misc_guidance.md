# Sync Server Miscellaneous Guidance

This document collects practical guidance for maintainable sync-source development.

## Choose the right sync path first

Before writing code, decide source type:

- **Time-series path** (`SyncManager`):
  - use for high-volume historical streams
  - supports adaptive windows, pagination, and overlap-safe incremental sync
- **Non-time-series path** (standalone module):
  - use for snapshots and daily aggregates
  - simpler logic and scheduling

Choosing the wrong path usually creates unnecessary complexity.

## Keep source contracts stable

For long-term maintainability:

- keep source naming in `SYNC_SOURCES` clear and stable
- keep payload shape (`data` keys) predictable for downstream UI/report usage
- avoid changing semantics of existing source outputs without migration and consumer review

## PrivX API usage guidance

When building source fetch logic:

- prefer existing `lib/report_api` wrappers where available
- if a new PrivX call pattern is reused, add a wrapper instead of repeating response/error handling
- keep normalization close to fetch/transform code so behavior is easy to review

## Idempotency and boundary safety

For time-series sources, preserve these guarantees:

- deterministic `record_id`
- overlap-safe incremental start behavior
- database-level dedupe (`ON CONFLICT DO NOTHING`)

For non-time-series sources, be explicit about update semantics:

- overwrite by timestamp (`on_conflict_do_update`) for snapshots, or
- insert-once semantics for daily records

## Migration and retention reminders

When adding a new source:

- table and retention behavior should be explicit in migration files
- do not rely on “implicit defaults” for retention expectations
- ensure admin migration workflows are documented for operators

## Keep docs implementation-aware, not implementation-heavy

Use implementation details to clarify extension points, not to narrate internals line-by-line.

Preferred style:

- short checklist + key file touch points
- one small snippet only when a contract is non-obvious
- links to deeper architecture/operations docs for internals and runtime operations

## Links

- [Back to development guide](../DEVELOPMENT_GUIDE.md)
