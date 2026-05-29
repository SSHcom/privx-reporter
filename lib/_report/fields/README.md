# Fields Configuration

Utilities for reading, validating, and displaying output fields from configuration.

## Public Functions

### `get_available_fields(config, report_path) -> dict[str, str]`

Get all available fields (excluding redacted) from configuration.

- **config**: Configuration dictionary (from config.toml)
- **report_path**: Path to report section (e.g., "access.subcommands.map")
- **Returns**: Mapping of field names to header labels

### `get_default_field_names(config, report_path) -> list[str]`

Extract default field names from configuration (fields marked as "true").

- **config**: Configuration dictionary (from config.toml)
- **report_path**: Path to report section (e.g., "access.subcommands.map")
- **Returns**: List of default field names in configuration order

### `validate_requested_fields(config, report_path, requested_fields) -> None`

Validate CLI-requested fields against configuration.

- **config**: Configuration dictionary (from config.toml)
- **report_path**: Path to report section (e.g., "access.subcommands.map")
- **requested_fields**: List of field names from CLI --fields option
- **Raises**: ValueError for invalid, missing, redacted, or duplicate fields

### `print_available_fields_and_exit(config, report_path) -> None`

Print available fields to stdout and exit.

- **config**: Configuration dictionary (from config.toml)
- **report_path**: Path to report section (e.g., "access.subcommands.map")
- **Raises**: ConfigError if no fields found or configuration invalid

## Field Flags (from config.toml)

- `true`: Included in default output
- `false`: Available via --fields but not in default
- `redact`: Excluded from all output (security)
