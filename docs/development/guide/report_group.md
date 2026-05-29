# Report Group

Describing a practical structure of a report group module (`reports/<group>/__init__.py`).

## Existing helpers you can reuse

Common group helpers are:

- `get_subcommand_config`: validates that config exists for `<group> <subcommand>`
- `make_report_ids`: builds report id metadata (`command`, `sub_command`, `report_prefix`, `config_key`)
- `get_requested_fields`: parses and validates CLI `--fields` for the selected report
- `get_report_inputs`: maps parsed CLI args into subcommand-specific input model
- `report_response`: returns standardized response dict for success/info/error outcomes
- `handle_error`: formats invalid-subcommand and other routing-level error messages

These helpers are optional, but they provide a consistent and low-friction default pattern across report groups.

## Helper args and returns (roles example)

Using `reports/roles/__init__.py` as reference:

### `get_subcommand_config`

Call example: `output_config = get_subcommand_config(config, "roles", subcommand)`

- args:
  - `config`: full loaded config dictionary
  - `"roles"`: group name
  - `subcommand`: selected report type (for example: `members`, `query`)
- returns:
  - the full `config` dict after validating `config["roles"]["subcommands"][subcommand]` exists
- raises:
  - `ConfigError` if that group/subcommand output section is missing

### `make_report_ids`

Call example: `report_ids = make_report_ids("roles", subcommand)`

- args:
  - `"roles"`: top-level report command/group
  - `subcommand`: selected subcommand name
- returns:
  - `ReportIds` dataclass with:
    - `command`: group name
    - `sub_command`: subcommand name
    - `report_prefix`: `<command>.<subcommand>` (used in filenames/logical report naming)
    - `config_key`: `<command>.subcommands.<subcommand>` (path string for field/config helpers)

### `get_requested_fields`

Call example: `requested_fields = get_requested_fields(args, config, report_ids.config_key)`

- args:
  - `args`: parsed CLI namespace (must include `fields` when enabled)
  - `config`: full loaded config dictionary
  - `report_ids.config_key`: report path string (for example: `roles.subcommands.members`)
- returns:
  - `None` when `--fields` is not provided (caller should use default configured fields)
  - `list[str]` when `--fields` explicitly selects/expands fields
  - in help mode (`--fields` without value), helper prints available fields and exits process
- raises:
  - `ValidationError` for invalid `--fields` values

### `get_report_inputs`

Call example: `report_inputs = get_report_inputs(MembersReportInputs, args)`


- args:
  - input model class (`MembersReportInputs`, etc.) that extends `BaseReportInputs`
  - `args`: parsed CLI namespace
- returns:
  - on success: instance of the requested input model with matching args populated
  - on validation failure: `BaseReportInputs` with `_error_message` set
- behavior:
  - only dataclass fields from the target input model are copied from `args` (extra CLI args are ignored)
  - required inputs are controlled by model `_mandatory` list (for example, roles models require `role_name` for members and `user_name` for user report)
  - required-field errors are normalized to CLI style in the message (snake_case -> kebab-case)
- handler pattern:
  - check `if report_inputs._error_message:` and return `report_response(error_message=...)`
  - after this check, cast to the concrete model type before passing to the report function

### Input models

`MembersReportInputs` is declared as:

```
@dataclass
class MembersReportInputs(BaseReportInputs):
    _mandatory: list[str] = field(default_factory=lambda: ["role_name"])
    role_name: str = ""
```

- The model contains all possible input arguments for the `members` sub-command
- `get_report_inputs` maps CLI args for the sub-command to the model
- `_mandatory` list contains all mandatory model properties
- Other input models for roles are: `QueryReportInputs`, `UserReportInputs`, `RestrictionsReportInputs`

## Why use the helpers?

In group handlers, this leads to a common pattern:
- `output_config` drives output behavior
- `report_ids` carries stable naming/context values to downstream report functions
- `requested_fields` controls whether default or explicit field selection is used
- `report_inputs` carries validated, subcommand-specific input data

## Example routing structure

A typical group handler flow is:

1. Read `args.subcommand`.
2. Resolve subcommand config + report ids + requested fields.
3. Early-return informational response when field selection is empty.
4. Route by subcommand name:
   - build subcommand-specific inputs
   - validate input conversion result
   - call the matching `reports/<group>/<report>/report.py` function
5. For unknown subcommand, return a standardized error/info response.

## Minimal rule

Implementation style can vary, but keep one stable contract:

- group handler returns a dict with `report_path`, `error_message`, and `info_message` (values or `None`)

If that contract is respected, the rest of the report pipeline can stay decoupled from internal routing details.

## Links

- Next: [Report input and group configuration](report_input_group_configuration.md)
- [Back to development guide](../DEVELOPMENT_GUIDE.md)
