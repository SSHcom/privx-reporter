# Report: Miscellaneous Guidance Topics

This document collects miscellaneous practical guidance for maintainable report implementations.

## PrivX API usage in reports

Reports can use the PrivX client directly (`api.<method>(...)`) or route calls through `apps/python/lib/report_api`.

For new report code, prefer `apps/python/lib/report_api` wrappers first.

Why:

- wrappers centralize common error handling behavior
- wrappers normalize response extraction patterns
- wrappers keep report modules smaller and more readable

Direct client usage is still valid for one-off calls, prototyping, or when no wrapper exists yet.

When introducing a new PrivX query path, create a wrapper in `apps/python/lib/report_api` instead of embedding repeated response/error handling in report modules.

## Choosing API vs database source

Some reports can be implemented either via PrivX API or local synced database:

- API path: fresher remote data, bounded by API behavior and limits
- data DB path (`use_database("data")`): local Timescale query, often better for heavy historical slicing and filtering

Use the source that best matches report intent. If you add both variants for the same report, keep input/output behavior consistent so users can switch without relearning semantics.

For database access:

- data DB: `use_database("data")`
- admin DB: `use_database("admin")`

Connection settings come from environment variables loaded through `EnvConfig` (`DB_DATA_*` and `DB_ADMIN_*`).

## Admin and sync database operations

Operational workflows that affect report data availability:

- apply migrations: `admin migration up`
- inspect migration state: `admin migration status`
- backfill missing historical data: `admin sync backfill --days <n>` or `admin sync backfill --from <YYYY-MM-DD>`

For detailed command behavior, use:

- `docs/operations/CLI_ADMIN_GUIDE.md`
- `docs/operations/SYNC_SERVER_GUIDE.md`
- `docs/operations/ENVIRONMENT_VARIABLES.md`

## CLI report impact on UI report experience

The report implementation is shared by CLI and UI execution paths.

As a result, reports built for CLI are also available to UI users unless explicitly hidden with report metadata.

Design implications:

- avoid unbounded fetches where possible
- prefer pagination/batching patterns for large datasets
- keep expensive joins/post-processing under control
- decide deliberately whether the report should be visible in UI (configure using `ui_display` in `out.toml` file)

`apps/python/lib/report_api/connections.py`:`search_connections(...)` is a good reference pattern for offset/limit paging with shared error handling.

## Performance defaults and guardrails

Practical guardrails for report development:

- always define and validate date ranges for high-volume datasets
- use batch size from `EnvConfig.get_api_batchsize()` for API paging
- for DB reports, push filters into SQL/query construction instead of Python post-filtering when feasible
- keep output field validation (`validate_dict_contains`) close to extraction/formatting to fail early with actionable errors

## Keep report contracts stable

Even when implementation details differ, keep the report contract predictable:

- input model parsed via report input dataclass
- output field set driven by `out.toml` and optional `--fields`
- return contract remains `{report_path, error_message, info_message}`

This stability is what allows CLI, UI, and future integrations to reuse the same report implementation surface.

## Links

- [Back to development guide](../DEVELOPMENT_GUIDE.md)
