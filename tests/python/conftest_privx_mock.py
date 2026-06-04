"""Mock for privx_api module to allow tests to run without installing it."""

import sys
from unittest.mock import MagicMock

# Create a mock module for privx_api
privx_api_mock = MagicMock()
privx_api_mock.PrivXAPI = MagicMock
privx_api_mock.exceptions = MagicMock()
privx_api_mock.exceptions.InternalAPIException = Exception

# Install the mock in sys.modules before any imports
sys.modules["privx_api"] = privx_api_mock
sys.modules["privx_api.exceptions"] = privx_api_mock.exceptions
