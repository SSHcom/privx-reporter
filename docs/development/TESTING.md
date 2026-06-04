# Testing Guide

This guide is the source of truth for testing in this repository.

## Core rules

- This is a UV project. Use `uv run ...` for direct Python tool execution.
- Prefer Task targets for standard test workflows.
- Do not use `python -m pytest` (it can run outside the project environment and fail with import/runtime mismatches).
- Pytest, coverage, ruff, and mypy are scoped to Python trees: `apps/python/`, `tests/python/`, and `live_test/`. The `tests/` package root keeps `tests/__init__.py`; runnable tests and shared fixtures live under `tests/python/` (mirroring `apps/python/`). Lint and type-check paths are defined in `Taskfile.yml` and `pyproject.toml`.

## Layout

Python tests mirror application packages under `tests/python/`:

- `tests/python/lib/` — `apps/python/lib/`
- `tests/python/reports/` — `apps/python/reports/`
- `tests/python/ui/` — `apps/python/ui/`
- `tests/python/administration/` — `apps/python/administration/`
- `tests/python/sync_server/` — `apps/python/sync_server/`
- `tests/python/backup_server/` — `apps/python/backup_server/`
- `tests/python/lib/_backup/` — `apps/python/lib/_backup/` (host backup archive CLI)

Shared test support (`conftest.py`, `fixtures/`, `helpers/`, `mocks/`) also lives under `tests/python/`. Imports may use the `tests.*` package name (see `tests/__init__.py`).

## Primary test commands

Run these from repository root:

```sh
task test
task test-unit
task test-integration
task test-cov
task test-cov-unit
task test-cov-integration
```

## Run focused tests

For a specific file or directory, use `pytest` directly through UV:

```sh
uv run pytest tests/python/lib/cli_engine/test_generator.py
uv run pytest tests/python/reports/roles/
```

Use markers when needed:

```sh
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m database
```

## Database schema parity test

Checks SQLAlchemy model tables against migrated live schema for:

- Column names
- Broad column type family
- Nullability
- Primary key column set

Use:

```sh
docker compose -f docker-compose-test.yml up -d
task test-database
```

Run `task test-database` after changes to:

- `apps/python/administration/migration/_files`
- `apps/python/lib/database/models/`

Reference: `tests/python/lib/database/models/test_schema_parity.py` (marker: `database`).

## Recommended verification flow for code changes

Use the smallest meaningful scope first, then expand:

1. Run focused tests for changed areas (`uv run pytest <path>`).
2. Run `task test-unit` for broader regression checks.
3. Run `task test-integration` when behavior crosses component boundaries.
4. Run `task test` before opening a PR or finalizing a change.

Use coverage targets when specifically validating test completeness (`task test-cov*`).

## Related references

- Live sync/load testing: `live_test/README.md`
- Administration operational details and migration context: `docs/operations/CLI_ADMIN_GUIDE.md`
