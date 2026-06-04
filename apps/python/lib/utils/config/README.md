# Output Configuration

Utilities for field selection and validation in report output.

## Public Functions

**Note**: When mentioning _Configuration dictionary_, we are referring to `reports/config.toml` which is file generated from all `in.toml` and `out.toml` files of the reports.

### `get_subcommand_config(config, group, subcommand) -> dict`

Get output configuration for a report subcommand.

- **config**: Configuration dictionary
- **group**: Report group name (e.g., "access", "connections", "roles")
- **subcommand**: Subcommand name (e.g., "map", "details", "query")
- **Returns**: Full config dict containing output configuration

### `get_requested_fields(args, config, report_path) -> list[str] | None`

Process --fields CLI option.

- **args**: Parsed command line arguments
- **config**: Configuration dictionary
- **report_path**: Path to report section (e.g., "access.subcommands.map")
- **Returns**: None for defaults, or validated field list
- **Note**: Prints available fields and exits if --fields used without value

### `get_field_names_and_headers(config, report_path, requested_fields) -> tuple[list[str], list[str]]`

Extract field names and headers from output configuration.

- **config**: Configuration dictionary
- **report_path**: Path to report section (e.g., "access.subcommands.map")
- **requested_fields**: Optional field list from CLI --fields (None for defaults)
- **Returns**: (field_names, header_labels)

## Field Flags

- `true`: Included in default output
- `false`: Available via --fields but not in default
- `redact`: Excluded from all output (security)

## Example Usage

```python
# In report handler
output_config = get_subcommand_config(config, "access", "map")
requested_fields = get_requested_fields(args, config, "access.subcommands.map")

# In report function
field_names, header_labels = get_field_names_and_headers(
    output_config, "access.subcommands.map", requested_fields=requested_fields
)
```
