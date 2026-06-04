"""Tests for secrets report functions."""

from unittest.mock import MagicMock

import pytest

from lib.utils.config.report_ids import ReportIds
from reports.list.secrets import report as secrets_module
from reports.list.secrets.models import SecretsReportInputs


@pytest.mark.unit
def test_list_secrets_success(
    mock_report_api_secrets: MagicMock,
    mock_env_config_secrets: MagicMock,  # noqa
    mock_csv_writer_secrets: MagicMock,  # noqa
    mock_output_config_secrets: dict,
    mock_report_ids_secrets: ReportIds,
    standard_csv_dir: str,
) -> None:
    """Test that list_secrets retrieves secrets and writes CSV."""
    mock_api = MagicMock()

    mock_report_api_secrets.search_secrets.return_value = {
        "count": 1,
        "items": [
            {
                "id": "secret-123",
                "name": "database-credentials",
                "path": "/prod/db",
                "read_roles": [{"id": "role-1", "name": "admin"}],
                "write_roles": [{"id": "role-1", "name": "admin"}],
            }
        ],
    }

    inputs = SecretsReportInputs()
    result = secrets_module.list_secrets(
        mock_api,
        mock_output_config_secrets,
        mock_report_ids_secrets,
        inputs,
        None,
    )

    assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}
    mock_report_api_secrets.search_secrets.assert_called_once_with(mock_api, offset=0, limit=200)


@pytest.mark.unit
def test_list_secrets_with_multiple_roles(
    mock_report_api_secrets: MagicMock,
    mock_env_config_secrets: MagicMock,  # noqa
    mock_csv_writer_secrets: MagicMock,  # noqa
    mock_output_config_secrets: dict,
    mock_report_ids_secrets: ReportIds,
    standard_csv_dir: str,
) -> None:
    """Test that list_secrets creates one row per unique secret-role combination."""
    mock_api = MagicMock()

    mock_report_api_secrets.search_secrets.return_value = {
        "count": 1,
        "items": [
            {
                "id": "secret-123",
                "name": "database-credentials",
                "path": "/prod/db",
                "read_roles": [
                    {"id": "role-1", "name": "admin"},
                    {"id": "role-2", "name": "reader"},
                ],
                "write_roles": [{"id": "role-1", "name": "admin"}],
            }
        ],
    }

    inputs = SecretsReportInputs()
    result = secrets_module.list_secrets(
        mock_api,
        mock_output_config_secrets,
        mock_report_ids_secrets,
        inputs,
        None,
    )

    assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}
    mock_report_api_secrets.search_secrets.assert_called_once_with(mock_api, offset=0, limit=200)


@pytest.mark.unit
def test_list_secrets_no_secrets_found(
    mock_report_api_secrets: MagicMock,
    mock_env_config_secrets: MagicMock,  # noqa
    mock_csv_writer_secrets: MagicMock,  # noqa
    mock_output_config_secrets: dict,
    mock_report_ids_secrets: ReportIds,
) -> None:
    """Test that list_secrets returns info message when no secrets found."""
    mock_api = MagicMock()

    mock_report_api_secrets.search_secrets.return_value = {
        "count": 0,
        "items": [],
    }

    inputs = SecretsReportInputs()
    result = secrets_module.list_secrets(
        mock_api,
        mock_output_config_secrets,
        mock_report_ids_secrets,
        inputs,
        None,
    )

    assert result == {"report_path": None, "error_message": None, "info_message": "No secrets found"}
    mock_report_api_secrets.search_secrets.assert_called_once_with(mock_api, offset=0, limit=200)
    mock_csv_writer_secrets.assert_not_called()


@pytest.mark.unit
def test_list_secrets_filters_by_name(
    mock_report_api_secrets: MagicMock,
    mock_env_config_secrets: MagicMock,  # noqa
    mock_csv_writer_secrets: MagicMock,  # noqa
    mock_output_config_secrets: dict,
    mock_report_ids_secrets: ReportIds,
    standard_csv_dir: str,
) -> None:
    """Test that list_secrets filters secrets by name."""
    mock_api = MagicMock()

    mock_report_api_secrets.search_secrets.return_value = {
        "count": 3,
        "items": [
            {
                "id": "secret-1",
                "name": "database-credentials",
                "path": "/prod/db",
                "read_roles": [{"id": "role-1", "name": "admin"}],
                "write_roles": [],
            },
            {
                "id": "secret-2",
                "name": "api-key",
                "path": "/prod/api",
                "read_roles": [{"id": "role-2", "name": "reader"}],
                "write_roles": [],
            },
            {
                "id": "secret-3",
                "name": "db-password",
                "path": "/prod/db",
                "read_roles": [{"id": "role-3", "name": "editor"}],
                "write_roles": [],
            },
        ],
    }

    inputs = SecretsReportInputs(name="db")
    result = secrets_module.list_secrets(
        mock_api,
        mock_output_config_secrets,
        mock_report_ids_secrets,
        inputs,
        None,
    )

    assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}


@pytest.mark.unit
def test_list_secrets_filters_by_read_role(
    mock_report_api_secrets: MagicMock,
    mock_env_config_secrets: MagicMock,  # noqa
    mock_csv_writer_secrets: MagicMock,  # noqa
    mock_output_config_secrets: dict,
    mock_report_ids_secrets: ReportIds,
    standard_csv_dir: str,
) -> None:
    """Test that list_secrets filters rows by read role."""
    mock_api = MagicMock()

    mock_report_api_secrets.search_secrets.return_value = {
        "count": 1,
        "items": [
            {
                "id": "secret-123",
                "name": "database-credentials",
                "path": "/prod/db",
                "read_roles": [
                    {"id": "role-1", "name": "admin"},
                    {"id": "role-2", "name": "reader"},
                ],
                "write_roles": [{"id": "role-1", "name": "admin"}],
            }
        ],
    }

    inputs = SecretsReportInputs(read_role="admin")
    result = secrets_module.list_secrets(
        mock_api,
        mock_output_config_secrets,
        mock_report_ids_secrets,
        inputs,
        None,
    )

    assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}


@pytest.mark.unit
def test_list_secrets_filters_by_write_role(
    mock_report_api_secrets: MagicMock,
    mock_env_config_secrets: MagicMock,  # noqa
    mock_csv_writer_secrets: MagicMock,  # noqa
    mock_output_config_secrets: dict,
    mock_report_ids_secrets: ReportIds,
    standard_csv_dir: str,
) -> None:
    """Test that list_secrets filters rows by write role."""
    mock_api = MagicMock()

    mock_report_api_secrets.search_secrets.return_value = {
        "count": 1,
        "items": [
            {
                "id": "secret-123",
                "name": "database-credentials",
                "path": "/prod/db",
                "read_roles": [
                    {"id": "role-1", "name": "admin"},
                    {"id": "role-2", "name": "reader"},
                ],
                "write_roles": [{"id": "role-1", "name": "admin"}],
            }
        ],
    }

    inputs = SecretsReportInputs(write_role="admin")
    result = secrets_module.list_secrets(
        mock_api,
        mock_output_config_secrets,
        mock_report_ids_secrets,
        inputs,
        None,
    )

    assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}


@pytest.mark.unit
def test_list_secrets_no_rows_after_filter(
    mock_report_api_secrets: MagicMock,
    mock_env_config_secrets: MagicMock,  # noqa
    mock_csv_writer_secrets: MagicMock,  # noqa
    mock_output_config_secrets: dict,
    mock_report_ids_secrets: ReportIds,
) -> None:
    """Test that list_secrets returns info message when filter results in no rows."""
    mock_api = MagicMock()

    mock_report_api_secrets.search_secrets.return_value = {
        "count": 1,
        "items": [
            {
                "id": "secret-123",
                "name": "database-credentials",
                "path": "/prod/db",
                "read_roles": [{"id": "role-1", "name": "admin"}],
                "write_roles": [{"id": "role-1", "name": "admin"}],
            }
        ],
    }

    inputs = SecretsReportInputs(read_role="nonexistent")
    result = secrets_module.list_secrets(
        mock_api,
        mock_output_config_secrets,
        mock_report_ids_secrets,
        inputs,
        None,
    )

    assert result == {"report_path": None, "error_message": None, "info_message": "No secrets found"}
    mock_csv_writer_secrets.assert_not_called()


@pytest.mark.unit
def test_list_secrets_no_output_config(
    mock_report_api_secrets: MagicMock,
    mock_env_config_secrets: MagicMock,  # noqa
    mock_csv_writer_secrets: MagicMock,  # noqa
    mock_report_ids_secrets: ReportIds,
) -> None:
    """Test that list_secrets returns error message when output config is missing."""
    mock_api = MagicMock()

    mock_report_api_secrets.search_secrets.return_value = {
        "count": 1,
        "items": [
            {
                "id": "secret-123",
                "name": "database-credentials",
                "path": "/prod/db",
                "read_roles": [{"id": "role-1", "name": "admin"}],
                "write_roles": [{"id": "role-1", "name": "admin"}],
            }
        ],
    }

    inputs = SecretsReportInputs()
    result = secrets_module.list_secrets(
        mock_api,
        {},
        mock_report_ids_secrets,
        inputs,
        None,
    )

    assert result["report_path"] is None
    assert result["error_message"] is not None
    assert result["info_message"] is None


@pytest.mark.unit
def test_list_secrets_with_requested_fields(
    mock_report_api_secrets: MagicMock,
    mock_env_config_secrets: MagicMock,  # noqa
    mock_csv_writer_secrets: MagicMock,  # noqa
    mock_output_config_secrets: dict,
    mock_report_ids_secrets: ReportIds,
    standard_csv_dir: str,
) -> None:
    """Test that list_secrets respects requested_fields parameter."""
    mock_api = MagicMock()

    mock_report_api_secrets.search_secrets.return_value = {
        "count": 1,
        "items": [
            {
                "id": "secret-123",
                "name": "database-credentials",
                "path": "/prod/db",
                "read_roles": [{"id": "role-1", "name": "admin"}],
                "write_roles": [{"id": "role-1", "name": "admin"}],
            }
        ],
    }

    inputs = SecretsReportInputs()
    result = secrets_module.list_secrets(
        mock_api,
        mock_output_config_secrets,
        mock_report_ids_secrets,
        inputs,
        ["name", "read_roles", "write_roles"],
    )

    assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}


@pytest.mark.unit
def test_list_secrets_case_insensitive_filter(
    mock_report_api_secrets: MagicMock,
    mock_env_config_secrets: MagicMock,  # noqa
    mock_csv_writer_secrets: MagicMock,  # noqa
    mock_output_config_secrets: dict,
    mock_report_ids_secrets: ReportIds,
    standard_csv_dir: str,
) -> None:
    """Test that list_secrets filters are case-insensitive."""
    mock_api = MagicMock()

    mock_report_api_secrets.search_secrets.return_value = {
        "count": 2,
        "items": [
            {
                "id": "secret-1",
                "name": "Database-Credentials",
                "path": "/prod/db",
                "read_roles": [{"id": "role-1", "name": "Admin"}],
                "write_roles": [],
            },
            {
                "id": "secret-2",
                "name": "api-key",
                "path": "/prod/api",
                "read_roles": [],
                "write_roles": [],
            },
        ],
    }

    inputs = SecretsReportInputs(name="database")
    result = secrets_module.list_secrets(
        mock_api,
        mock_output_config_secrets,
        mock_report_ids_secrets,
        inputs,
        None,
    )

    assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}


@pytest.mark.unit
def test_list_secrets_read_and_write_access_flags(
    mock_report_api_secrets: MagicMock,
    mock_env_config_secrets: MagicMock,  # noqa
    mock_csv_writer_secrets: MagicMock,  # noqa
    mock_output_config_secrets: dict,
    mock_report_ids_secrets: ReportIds,
    standard_csv_dir: str,
) -> None:
    """Test that read_roles and write_roles flags are set correctly."""
    mock_api = MagicMock()

    mock_report_api_secrets.search_secrets.return_value = {
        "count": 1,
        "items": [
            {
                "id": "secret-123",
                "name": "database-credentials",
                "path": "/prod/db",
                "read_roles": [{"id": "role-1", "name": "admin"}, {"id": "role-2", "name": "reader"}],
                "write_roles": [{"id": "role-1", "name": "admin"}],
            }
        ],
    }

    inputs = SecretsReportInputs()
    result = secrets_module.list_secrets(
        mock_api,
        mock_output_config_secrets,
        mock_report_ids_secrets,
        inputs,
        None,
    )

    assert result == {"report_path": standard_csv_dir, "error_message": None, "info_message": None}
