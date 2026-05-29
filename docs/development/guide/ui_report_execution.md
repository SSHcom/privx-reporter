# UI Report Execution

This document describes how report execution works in the UI and where to extend it safely.

## Execution Flow

At runtime, report execution path is:

1. Report selection from sidebar/session state.
2. Access check in `can_access_report(...)`.
3. Form rendering from report TOML metadata.
4. Form values mapped to CLI-like args namespace.
5. Shared engine call (`generate(...)`).
6. File output read back for UI display.

Core modules:

- `ui/pages/_2_Reports.py`
- `ui/components/report/report.py`
- `ui/components/report/partials/report_option_inputs.py`
- `ui/services/report_service.py`

## Config-Driven Forms

UI report forms are driven by `reports/config.toml` (loaded via `ui/services/config_service.py`).

Per report metadata controls rendering behavior:

- `type`, `required`, `help`
- `action=store_true` / boolean options
- `ui_hidden` for hidden options
- `ui_warning` for per-report warning text
- `ui_display` for optional in-page result display
- `ui_list` for dynamic select values

This keeps input structure aligned with report configuration instead of hardcoded page-specific forms.

## Running a Report

`run_report(...)` in `ui/services/report_service.py` handles execution:

1. Build `argparse.Namespace` with `command` and `subcommand`.
2. Attach form values and optional selected fields.
3. For `list` command, force `to_file=True` so UI can load output.
4. Set temporary `REPORT_OUT_DIR` to user-scoped directory.
5. Call `lib._report.generator.generate(api, args, config, user_group_id=...)`.
6. Restore original `REPORT_OUT_DIR`.
7. Optionally load CSV/JSON for page display.

## Output Directory Model

UI writes to:

`<REPORT_OUT_DIR>/<group>/<username>`

This comes from `get_user_output_dir()` and is created on demand.

Why this matters:

- isolates user outputs,
- supports admin “all files” view across users/groups,
- avoids collisions from same report names across users.

## Report Visibility and Access

UI access is deny-by-default:

- `get_viewable_reports()` fetches `(group_name, report_name)` pairs for current user.
- `can_access_report(primary, subcommand)` blocks unavailable reports.
- admin users bypass report visibility checks.

This is enforced both for report execution and report files browsing.

## Non-Admin Data Filtering Contract

For non-admin users, UI passes `user_group_id` into `generate(...)`.

Compatible report handlers then apply server-side filtering (for access-group scoped report families).

Result: UI does not rely only on hidden buttons; data scope is enforced at report execution path.

## Dynamic `ui_list` Values

For options with `ui_list`, the UI calls:

- `get_ui_list_values(command, subcommand, list_key)`
- internally uses shared `get_list(...)` helper

Behavior:

- access is checked before list fetch,
- on fetch errors/empty list, input falls back to plain text input.

## File Rendering Path

After a run, page stores result state and uses:

- `render_report_result(...)` for direct output
- `render_report_files(...)` for file list/download management

Dedicated files page (`_3_Report_Files.py`) provides broader browse/delete/download workflow.

## Extension Checklist

When adding a new report and expecting UI support:

1. Add report TOML definitions and regenerate `reports/config.toml`.
2. Confirm report appears in UI config and admin report mapping tables.
3. Verify form renders correctly from option metadata.
4. Verify access behavior for admin and non-admin users.
5. Verify output path and file display behavior.

## Links

- Next: [UI auth and OIDC](ui_auth_oidc.md)
- [Back to development guide](../DEVELOPMENT_GUIDE.md)
