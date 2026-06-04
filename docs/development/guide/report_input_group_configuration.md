# Report Input and Group Configuration

This document describes how report groups and report inputs are configured for CLI usage.

It focuses on `group.toml` and `in.toml` files and how they are consumed by the reporter.

## Overview

Input configuration defines CLI arguments for each report subcommand through `in.toml` files in report directories.

Group-level help and description are defined in an optional `group.toml` file at the group root.

## File layout

Each report group has an optional `group.toml`, and each subcommand has its own `in.toml`:

```text
apps/python/reports/
└── roles/
    ├── group.toml
    └── user/
        ├── in.toml
        ├── report.py
        └── out.toml
```

## `group.toml` format

`group.toml` defines group-level help text used by CLI help output:

- `help`: one-line summary shown in `bin/report --help`
- `description`: multi-line text for `bin/report <group> --help`

Example:

```toml
[roles]
help = "Reports about roles, their members and restrictions"
description = """\
Reports about roles, their members and restrictions.

Subcommands:
  members       List all members of a role
  query         Query roles by various filters
  restrictions  List roles with contextual restrictions enabled
  user          List all roles assigned to a user
"""
```

## `in.toml` format

Each `in.toml` uses hierarchical naming so all report configs can be merged into one combined config.

Example:

```toml
[roles.subcommands.user]
help = "Get roles of a user"

[roles.subcommands.user.options.user_id]
flags = ["--user-id", "-u"]
required = true
help = "User ID to filter by"

[roles.subcommands.user.options.verbose]
flags = ["--verbose", "-v"]
action = "store_true"
help = "Enable verbose output"
```

## Loading and parsing flow

1. `bin/combine_configs.sh` scans report TOML files (`group.toml`, `in.toml`, `out.toml`) and writes combined output to `apps/python/reports/config.toml`.
2. Reporter CLI loads combined config and parses commands/subcommands/options using `apps/python/lib/_report/cli_parser.py`.
3. Required argument rules are validated from TOML-driven config.
4. Help output is generated from the same config (`-h` and `--help`).

Notes:

- Group tables from `group.toml` are written before subcommand tables.
- CLI parser reads option definitions from `subcommands.<name>.options.<option_name>` dictionary entries.
- Non-dictionary values under `.options` (for example UI metadata from `out.toml`) are ignored by CLI option parsing.

## Option patterns

### Value option

```toml
[<command>.subcommands.<subcommand>.options.<option>]
flags = ["--year", "-y"]
required = true
help = "Option description"
```

### Boolean switch

```toml
[<command>.subcommands.<subcommand>.options.<option>]
flags = ["--verbose", "-v"]
action = "store_true"
help = "Enable verbose output"
```

`action = "store_true"` means the option is a presence flag:

- default value is `False` when the flag is not provided
- value becomes `True` when the flag is present
- no extra value is passed after the flag (for example: `--verbose`, not `--verbose true`)

### Optional value with default

```toml
[<command>.subcommands.<subcommand>.options.<option>]
flags = ["--format", "-f"]
default = "csv"
help = "Output format (csv, json)"
```

## `ui_list` value provider contract

Options can declare `ui_list` in `in.toml` to request dynamic list values.

Example:

```toml
[events.subcommands.query.options.event_name]
flags = ["--event-name"]
required = false
ui_list = "event_names"
help = "Filter by event name"
```

`ui_list` does not change CLI parsing behavior. It only declares a list key to resolve.

As a concrete example of list-handler usage, see `apps/python/reports/events/query`.

To support a list key:

1. Implement group-level route in `apps/python/reports/<group>/__init__.py`:
   - `get_list(subcommand: str, list_key: str)`
   - `list_key` is an identifier string (for example `event_names`) that tells the list handler which value list to return. Using identifiers allows one handler to support multiple lists.

2. Implement subcommand-level provider (for example `apps/python/reports/<group>/<subcommand>/ui.py`):
   - `get_list(list_key: str)`

Both return `UIListResponse` (`apps/python/lib/_report/generator.py`) with:

- `values`: list of strings
- `error_message`: `None` on success, message on failure

## Links

- Next: [Report output configuration](report_output_configuration.md)
- [Back to development guide](../DEVELOPMENT_GUIDE.md)
