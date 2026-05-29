## Development Guide

This section collects developer-facing guides for the reporter codebase.

Documents are intentionally small and presented in reading order to avoid overwhelming the reader and provide a smoother introduction to creating and maintaining reports and dependencies such as the sync server and CLI admin tool.

The recommended development approach is example-first.

Some topics like "Sync Server: time series" and "UI: OIDC" are complex and difficult to document without going into too much detail. To gain a proper understanding, reading the guides without investigating existing code will likely not be enough.

## Report development

1. [Reports high-level architecture](guide/reports_hl_architecture.md)
2. [Reports bootstrapping](guide/reports_bootstrapping.md)
3. [Report group](guide/report_group.md)
4. [Report input and group configuration](guide/report_input_group_configuration.md)
5. [Report output configuration](guide/report_output_configuration.md)
6. [Report misc guidance](guide/report_misc_guidance.md)

### Recommended approach

1. Pick an existing report that is close to what you are building.
2. Replicate its implementation style and structure in your new report.
3. Use the documents above as focused references when each topic comes up (bootstrapping, group routing, input config, output config, and so on).

This keeps implementation aligned with established patterns and reduces unnecessary design work.

## Sync server development

1. [Sync server high-level architecture](guide/sync_server_hl_architecture.md)
2. [Sync server bootstrapping](guide/sync_server_bootstrapping.md)
3. [Sync source: non-time-series](guide/sync_source_non_time_series.md)
4. [Sync source: time-series](guide/sync_source_time_series.md)
5. [Sync deterministic record IDs](guide/sync_deterministic_record_ids.md)
6. [Sync server misc guidance](guide/sync_server_misc_guidance.md)

### Recommended approach

For sync server development, the most productive approach is also example-first:

1. Pick an existing sync source that is close to what you are building.
2. Replicate its implementation style and structure in your new source.
3. Use the documents above as focused references when each topic comes up (startup wiring, source registration, window behavior, deterministic IDs, and so on).

This keeps implementation aligned with established patterns and reduces unnecessary design work.

Time-series sync is more complex than most report paths, so even with these guides, reading the existing sync code is usually still necessary.

## UI development

1. [UI high-level architecture](guide/ui_hl_architecture.md)
2. [UI bootstrapping](guide/ui_bootstrapping.md)
3. [UI pages and navigation](guide/ui_pages_navigation.md)
4. [UI report execution](guide/ui_report_execution.md)
5. [UI auth and OIDC](guide/ui_auth_oidc.md)
6. [UI OIDC login success path](guide/ui_oidc_login_success_path.md)

### Recommended approach

1. Pick an existing UI page or service that is close to what you are building.
2. Replicate its implementation style and structure in your new page/service.
3. Use the documents above as focused references when each topic comes up (startup wiring, page routing, report execution, auth/session behavior, and so on).

This keeps implementation aligned with established patterns and reduces unnecessary design work.

Dashboard data-fetching/widget internals are expected to change in the near term, so it will not be covered by this guide.
