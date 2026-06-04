"""Shared fixtures for lib/report_api tests."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_response() -> MagicMock:
    """Standard mock API response object with common attributes."""
    response = MagicMock()
    response.ok = True
    response.status = 200
    response.data = {}
    return response


@pytest.fixture
def mock_handle_http_5xx_error() -> Generator[MagicMock]:
    """Fixture for mocking handle_http_5xx_error in connections module."""
    with patch("lib.report_api.connections.handle_http_5xx_error") as mock:
        yield mock
