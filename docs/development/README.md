# Development

Developer-focused reference for code structure, workflows, tooling, and implementation pitfalls.
For operational or non-coding usage guides, see `[docs/operations](../operations/README.md)`.
For focused implementation guides, start with `[DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)` and `[guide/](guide/)`.

## Prerequisites

- Git
- Docker
- Python 3.13 or later
- `uv` package manager
  - If you cannot install `uv` through your Linux package manager or Homebrew, install it manually:
    - `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [Docker Buildx](https://github.com/docker/buildx)
  - Needed for creating distributable containers for the CLI Installer, UI and Sync server. Can be skipped for development and/or running components directly from the repository.

## Project Structure

```
 ├── lib/                         # Shared code library
 │   ├── clients/                 # Client initialization (privx, database)
 │   ├── report_api/              # PrivX API calls
 │   ├── utils/                   # Various utils/helpers
 │   ├── _report/                 # Reporter CLI entry point and routing
 │   └── _admin/                  # Administration CLI entry point and routing
 │
 ├── sync_server/                 # Sync server that syncs time-series data to a database
 │   └── main.py                  # Main server entry point
 │
 ├── reports/                     # Report implementations
 │   ├── roles/                   # Role-related reports
 │   ├── connections/             # Connection reports
 │   ├── access/                  # Access-related reports
 │   └── config.toml              # Combined CLI configuration (generated)
 │
 ├── administration/              # Administration modules (CLI-first, UI-planned)
 │   └── config.toml              # Combined CLI configuration (generated)
```

## Read This First (Common Pitfalls)

Before starting development tasks, review [Essential Developer Notices](#essential-developer-notices). The following sections cover the most common pitfalls that cause confusing breakages:

- [Combined configuration files](#combined-configuration-files) - regenerate combined configs after changing report/administration TOML metadata.
- [Database SSL](#database-ssl) - required certificate setup when SSL modes are enabled.

## Taskfile

This project uses a `Taskfile` to define repeatable development commands, similar to a `Makefile` or `package.json` scripts.

Many commands referenced in this document are `task` commands (for example, linting, type checking, and tests).

To see all available tasks, run:

```bash
task
```

## Development Tasks

### Linting

- `task lint` - Run format checking with ruff
- `task format` - Apply safe code formatting with ruff
- `task type-check` - Check for type errors with `mypy`

**What to run?**

- After code changes run both `lint` and `type-check` tasks
- Run `format` to safely auto-fix some ruff formatting errors
- Type errors are to be fixed manually

**Hint:** To save time - use AI for fixing. Formatting and type errors are mostly trivial for an AI to correct.

### Testing

This project uses [pytest](https://pytest.org/) for unit testing.

**Running Tests:**

- `task test` - Run all tests with pytest
- `task test-unit` - Run only unit tests
- `task test-integration` - Run only integration tests
- `task test-cov` - Run all tests with coverage report
- `task test-cov-unit` - Run unit tests with coverage report
- `task test-cov-integration` - Run integration tests with coverage report

You can also run pytest directly:

```bash
uv run pytest tests/lib/utils/       # Run tests in a specific directory
uv run pytest -k test_string         # Run tests matching a pattern
uv run pytest -m unit                # Run only unit tests
uv run pytest -m integration         # Run only integration tests
uv run pytest -v                     # Verbose output
```

**Test Structure:**

The test directory structure mirrors the source code structure:

```
tests/
 ├── lib/
 │   ├── utils/
 │   │   ├── test_csv_writer.py
 │   │   └── etc
 │   └── etc
 └── etc
```

**Writing Tests:**

- Test files should be named `test_*.py` or `*_test.py`
- Test functions should start with `test_`
- Place test files in the corresponding directory structure under `tests/`
- Use pytest fixtures for setup/teardown and shared test data
- Mark tests with `@pytest.mark.unit` or `@pytest.mark.integration` as appropriate

**Example:**

```python
from lib.utils.string import sanitize_string

@pytest.mark.unit
def test_sanitize_string_basic():
    """Test basic string sanitization."""
    assert sanitize_string("Hello World") == "hello-world"
```

## Running Components

Use [QUICK_START.md](QUICK_START.md) as the canonical step-by-step setup and runtime guide.

This document intentionally stays descriptive and focuses on conventions and structure.

### Command entry points

- CLI reporter: `bin/report <arguments>`
- CLI administration: `bin/admin <arguments>`
- Sync server: `bin/serve_sync`
- UI server: `bin/serve_ui`

Production-oriented examples are documented in [release/README.md](../release/README.md).

## Essential Developer Notices

### Database SSL

If using `DB_DATA_SSL_MODE=on` and/or `DB_ADMIN_SSL_MODE=on`, follow the PostgreSQL certificate instructions in [release/README.md](../release/README.md#ssl-db_data_ssl_modeon--db_admin_ssl_modeon) to avoid startup failures. This applies to both `docker-compose-db.yml` and `release/docker-compose.yml`.

### Combined configuration files

When you modify report or administration command configuration files, regenerate combined config outputs with `task combine-configs` or `bin/tasks/combine_configs.sh`.

Relevant source files:

- Report `group.toml` files (`reports/<group>/group.toml`)
- Report `in.toml` or `out.toml` files (`reports/<group>/<report>/in.toml`)
- Administration `group.toml` files (`administration/<group>/group.toml`)
- Administration `in.toml` files (`administration/<group>/<module>/in.toml`)

Generated outputs:

- `reports/config.toml`
- `administration/config.toml`

Without regeneration, command metadata changes are not applied and related CLI/UI behavior can break.

### Administration metadata consistency

Administration modules are currently CLI-driven (`bin/admin ...`) and are expected to become callable from the UI. At the moment, administration commands primarily manage which audit events are enabled for sync. Keep administration module metadata (`in.toml`) and module layout (`administration/<group>/<module>/module.py`) consistent so UI integration can rely on the same source metadata.

See [Administration Operational Guide](../operations/CLI_ADMIN_GUIDE.md) for current command usage, data files, and extension conventions.