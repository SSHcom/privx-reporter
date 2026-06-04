"""Hardcoded database settings for the live-test harness (docker-compose-test.yml)."""

from __future__ import annotations

import os

# Single physical Postgres instance; admin and data logical DBs share these settings.
TEST_DB_HOST = "localhost"
TEST_DB_PORT = "5446"
TEST_DB_USER = "postgres"
TEST_DB_PASSWORD = "postgres"
TEST_DB_NAME = "reporter_test"
TEST_DB_SSL_MODE = "off"


def apply_live_test_db_env() -> None:
    """Set DB_* env vars for live tests. Ignores project .env and shell overrides."""
    for prefix in ("DB_DATA_", "DB_ADMIN_"):
        os.environ[f"{prefix}HOST"] = TEST_DB_HOST
        os.environ[f"{prefix}PORT"] = TEST_DB_PORT
        os.environ[f"{prefix}USER"] = TEST_DB_USER
        os.environ[f"{prefix}PASSWORD"] = TEST_DB_PASSWORD
        os.environ[f"{prefix}NAME"] = TEST_DB_NAME
        os.environ[f"{prefix}SSL_MODE"] = TEST_DB_SSL_MODE
