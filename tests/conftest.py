"""Shared pytest fixtures for all tests."""

# Mock privx_api before any other imports to avoid dependency issues
from unittest.mock import MagicMock

import pytest

from .conftest_privx_mock import *  # noqa: F401,F403


@pytest.fixture
def mock_api() -> MagicMock:
    """Standard mock API object."""
    return MagicMock()


@pytest.fixture
def standard_csv_dir() -> str:
    """Standard CSV output directory for tests."""
    return "/test/report_out"


@pytest.fixture
def standard_batch_size() -> int:
    """Standard API batch size for tests."""
    return 100


@pytest.fixture
def mock_env_config_base(standard_csv_dir: str, standard_batch_size: int) -> MagicMock:
    """Base mock for EnvConfig with standard return values."""
    mock = MagicMock()
    mock.get_report_out_dir.return_value = standard_csv_dir
    mock.get_api_batchsize.return_value = standard_batch_size
    return mock
