"""Tests for secrets API functions."""

from unittest.mock import MagicMock

import pytest

from lib.report_api.secrets import get_secrets


@pytest.mark.unit
def test_get_secrets_success(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_secrets correctly retrieves and returns secrets."""
    mock_response.data = {
        "count": 2,
        "items": [
            {"id": "secret1", "name": "database-credentials"},
            {"id": "secret2", "name": "api-key"},
        ],
    }
    mock_api.get_secrets.return_value = mock_response

    result = get_secrets(mock_api)

    assert result["count"] == 2
    assert len(result["items"]) == 2
    mock_api.get_secrets.assert_called_once()


@pytest.mark.unit
def test_get_secrets_with_resp_not_ok(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_secrets returns None when the API response indicates an error."""
    mock_response.ok = False
    mock_response.status = 500
    mock_response.data = {"details": {"error_code": "INTERNAL_ERROR"}}
    mock_api.get_secrets.return_value = mock_response

    result = get_secrets(mock_api)

    assert result is None


@pytest.mark.unit
def test_get_secrets_with_status_400_in_data(mock_api: MagicMock, mock_response: MagicMock) -> None:
    """Test that get_secrets returns None when response data contains an error status code."""
    mock_response.data = {
        "status": 400,
        "details": {"error_code": "BAD_REQUEST"},
    }
    mock_api.get_secrets.return_value = mock_response

    result = get_secrets(mock_api)

    assert result is None


@pytest.mark.unit
def test_get_secrets_with_internal_api_exception(mock_api: MagicMock) -> None:
    """Test that get_secrets calls sys.exit on InternalAPIException."""
    import privx_api.exceptions

    api_exception = privx_api.exceptions.InternalAPIException("Internal error")
    mock_api.get_secrets.side_effect = api_exception

    with pytest.raises(SystemExit):
        get_secrets(mock_api)
