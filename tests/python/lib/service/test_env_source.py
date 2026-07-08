"""Tests for lib/service/env_source.py."""

from unittest.mock import patch

import pytest

from lib.service import env_source as env_source_module
from lib.service.env_source import EnvSource, getEnv


@pytest.fixture(autouse=True)
def reset_env_source_cache() -> None:
    env_source_module._env_source._db_values = None
    yield
    env_source_module._env_source._db_values = None


@pytest.mark.unit
@patch.dict(
    "os.environ",
    {
        "ENV_SOURCE": "db",
        "DB_ADMIN_SSL_MODE": "on",
        "PRIVX_API_CLIENT_ID": "from-env",
    },
    clear=True,
)
@patch.object(EnvSource, "_read_db_values", return_value={"PRIVX_API_CLIENT_ID": "from-db"})
def test_db_source_reads_db_values(_mock_read_db_values: object) -> None:
    assert getEnv("PRIVX_API_CLIENT_ID", "") == "from-db"


@pytest.mark.unit
@patch.dict(
    "os.environ",
    {
        "ENV_SOURCE": "db",
        "DB_ADMIN_SSL_MODE": "on",
        "PRIVX_API_CLIENT_ID": "from-env",
    },
    clear=True,
)
@patch.object(EnvSource, "_read_db_values", return_value={})
def test_db_source_falls_back_to_process_env(_mock_read_db_values: object) -> None:
    assert getEnv("PRIVX_API_CLIENT_ID", "") == "from-env"


@pytest.mark.unit
@patch.dict(
    "os.environ",
    {
        "ENV_SOURCE": "db",
        "DB_ADMIN_SSL_MODE": "on",
        "PRIVX_API_CLIENT_ID": "from-env",
    },
    clear=True,
)
@patch.object(EnvSource, "_read_db_values", return_value={"PRIVX_API_CLIENT_ID": ""})
def test_db_source_keeps_empty_db_value(_mock_read_db_values: object) -> None:
    assert getEnv("PRIVX_API_CLIENT_ID", "default") == ""


@pytest.mark.unit
@patch.dict("os.environ", {"ENV_SOURCE": "env", "PRIVX_API_CLIENT_ID": "from-env"}, clear=True)
@patch.object(EnvSource, "_read_db_values", return_value={"PRIVX_API_CLIENT_ID": "from-db"})
def test_env_source_ignores_db_values(_mock_read_db_values: object) -> None:
    assert getEnv("PRIVX_API_CLIENT_ID", "") == "from-env"
