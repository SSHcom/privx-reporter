"""Tests for list local users report."""

from unittest.mock import MagicMock, patch

import pytest

from reports._shared.input import BaseReportInputs
from reports.list.local_users.report import list_local_users
from tests.reports.list.helpers import output_config, report_ids


@pytest.mark.unit
def test_list_local_users_success_and_output_config_failure() -> None:
    config = output_config("local-users", {"id": "true|ID", "username": "true|Username"})
    with (
        patch("reports.list.local_users.report.report_api") as mock_report_api,
        patch("reports.list.local_users.report.write_report_output") as mock_write,
    ):
        mock_report_api.users.get_all_users.return_value = [
            {"id": "u-1", "username": "alice", "full_name": "", "email": ""}
        ]
        mock_write.return_value = {"report_path": "/tmp/local-users.csv", "error_message": None, "info_message": None}
        result = list_local_users(MagicMock(), config, report_ids("local-users"), BaseReportInputs())
    assert result["report_path"] == "/tmp/local-users.csv"

    with patch("reports.list.local_users.report.report_api") as mock_report_api:
        mock_report_api.users.get_all_users.return_value = [{"id": "u-1", "username": "alice"}]
        fail_result = list_local_users(MagicMock(), {}, report_ids("local-users"), BaseReportInputs())
    assert "Output configuration is required" in fail_result["error_message"]
