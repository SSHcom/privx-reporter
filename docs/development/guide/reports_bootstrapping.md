# Reports Bootstrapping

This document describes the minimal wiring needed to add or maintain a report.

It focuses on the execution contract between:

- `reports/<group>/__init__.py`
- `reports/<group>/<report>/report.py`

This is intentionally a high-level guide. Internal helper patterns are covered in separate documents.

## What `reports/<group>/__init__.py` does

Each report group module acts as a group-level router.

Its responsibility is to:

1. Receive the selected CLI command context from the report generator.
2. Inspect the selected subcommand.
3. Route execution to the matching report module in `reports/<group>/<report>/report.py`.
4. Return the report response back to the shared reporter flow.

Using `roles` as an example, `reports/roles/__init__.py` routes subcommands such as `members`, `query`, `restrictions`, and `user` to their corresponding report modules.

## Group handler signature

At group level, the expected handler shape is:

`handle(api, args, config, user_group_id=None)`

Parameter roles at a high level:

- `api`: authenticated PrivX API client
- `args`: parsed CLI arguments for the selected command/subcommand
- `config`: combined reporter configuration (`reports/config.toml`)
- `user_group_id`: UI-specific access scope

`user_group_id` is used by UI-driven execution to limit accessible data. Currently this is used to filter PrivX data related to specific access groups.

## What to pass to `reports/<group>/<report>/report.py`

At minimum, the report function should receive:

- API client (used to fetch report data)
- Parsed report inputs (mapped from CLI args for that subcommand)
- Output configuration for that report
- Report identifiers (used for naming and config lookup)
- Optional requested fields from CLI `--fields` (if provided)

The exact type names can vary by report, but the handoff pattern should stay consistent: group module prepares the context, report module executes report logic.

## How report config arguments are given

Report CLI arguments are not hardcoded in the parser.

They are defined in report TOML files, combined into `reports/config.toml`, and parsed before the group handler runs. By the time `reports/<group>/__init__.py` is called, arguments are available through the parsed args namespace for the selected command/subcommand.

In practice, this means the group handler receives already-parsed CLI inputs and passes subcommand-specific inputs forward to the report module.

## What the report needs to return

The report flow expects the group handler/report flow to return a response dictionary with this outcome contract:

- `report_path`: output file path when a file is produced, otherwise `None`
- `error_message`: error text when execution fails, otherwise `None`
- `info_message`: informational text for non-error outcomes, otherwise `None`

This response is propagated back through the group handler to the main reporter flow, where error/info handling is finalized.

As long as this contract is respected, implementation details are up to the developer. This is why deeper implementation guides are useful but, in theory, optional.

## Minimal mental model

```text
CLI args (from combined config)
  -> reports/<group>/__init__.py
  -> reports/<group>/<report>/report.py
  -> {report_path, error_message, info_message}
```

## Links

- Next: [Report group](report_group.md)
- [Back to development guide](../DEVELOPMENT_GUIDE.md)
