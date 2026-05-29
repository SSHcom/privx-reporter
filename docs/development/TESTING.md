# Testing Guide

This guide is the source of truth for testing in this repository.

## Core rules

- This is a UV project. Use `uv run ...` for direct Python tool execution.
- Prefer Task targets for standard test workflows.
- Do not use `python -m pytest` (it can run outside the project environment and fail with import/runtime mismatches).

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
uv run pytest tests/lib/cli_engine/test_generator.py
uv run pytest tests/reports/roles/
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

- `administration/migration/_files`
- `lib/database/models/`

Reference: `tests/lib/database/models/test_schema_parity.py` (marker: `database`).

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
