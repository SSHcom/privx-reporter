# Report Output Configuration

This document describes how report output fields are configured through `out.toml`.

## Overview

Output configuration defines which fields are included by default in report output.

Default field sets are defined per report subcommand in `out.toml`, and can be overridden with `--fields`.

The same field selection applies to both CSV and JSON output because report rows are filtered before output formatting.

## File layout

Each report subcommand has its own `out.toml`:

```text
reports/
└── roles/
    ├── group.toml
    └── members/
        ├── in.toml
        ├── report.py
        └── out.toml
```

All `out.toml` files are merged into `reports/config.toml` together with matching `in.toml` files, using hierarchical TOML names.

## `out.toml` format

Example:

```toml
[roles.subcommands.members.fields]
role_name = "true|Role Name"
principal = "true|Principal"
full_name = "true|Full Name"
email = "true|Email"
access_group_name = "true|Access Group Name"
role_id = "false|Role ID"

[roles.subcommands.members.options]
ui_display = true
```

`[<command>.subcommands.<subcommand>.fields]` identifies the report, and each field value is:

`<selection_flag>|<header_label>`

Where:

- field key is canonical field name used by report logic
- header label is the output header text

## Selection flags

- `true`: include in default output
- `false`: exclude from default output
- `redact`: always unavailable due to sensitivity

## UI metadata in `out.toml`

`out.toml` may include UI metadata under:

```toml
[<command>.subcommands.<subcommand>.options]
ui_display = true
ui_warning = "..."
```

These values are metadata for UI consumers and are not treated as CLI flags.

- `ui_display`: controls whether report output is allowed to be displayed in the UI. Set this to `false` for reports that may generate too much output for practical UI rendering.
- `ui_warning`: optional extra warning text shown on the report page.

## `--fields` behavior

`--fields` can override default field selection:

- not provided: use defaults from `out.toml`
- `--fields`: print available fields
- `--fields <field>,<field>`: include only listed fields in listed order
- `--fields all`: include all non-redacted fields
- `--fields *,<field>`: expand `*` to current defaults and append explicit fields

Requested fields are validated against configured field names in `out.toml`. Redacted fields remain unavailable even when explicitly requested.

## Report-specific exceptions

Some reports may include output overrides. As an example `events query` provides `--json-source` that, when used, writes original event JSON directly to output. In that mode, `out.toml` field filtering is bypassed by implementation.

## Links

- Next: [Report misc guidance](report_misc_guidance.md)
- [Back to development guide](../DEVELOPMENT_GUIDE.md)
