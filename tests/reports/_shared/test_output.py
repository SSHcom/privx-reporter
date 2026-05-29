"""Tests for shared report output utilities."""

from unittest.mock import MagicMock, patch

import pytest

from reports._shared.input import BaseReportInputs
from reports._shared.output import write_report_output


@pytest.fixture
def sample_data() -> tuple[str, list[str], list[str], list[dict]]:
    """Provide common test data."""
    return (
        "test_report",
        ["id", "name"],
        ["ID", "Name"],
        [{"id": "1", "name": "Test"}, {"id": "2", "name": "Other"}],
    )


@pytest.mark.unit
@pytest.mark.parametrize("to_stdout", [False, True])
@patch("reports._shared.output.CsvWriter")
@patch("reports._shared.output.EnvConfig.get_report_out_dir", return_value="/report/out")
def test_write_csv_output_destinations(
    mock_env: MagicMock,
    mock_csv_writer: MagicMock,
    sample_data: tuple,
    to_stdout: bool,
) -> None:
    """CSV output should support file and stdout destinations."""
    report_prefix, field_names, header_labels, output_data = sample_data
    if not to_stdout:
        mock_csv_writer.return_value.write_to_file.return_value = "/report/out/test.csv"
    inputs = BaseReportInputs(to_json=False, to_stdout=to_stdout)

    result = write_report_output(
        report_prefix=report_prefix,
        inputs=inputs,
        field_names=field_names,
        header_labels=header_labels,
        output_data=output_data,
    )

    mock_csv_writer.assert_called_once_with(report_prefix, field_names, output_data, header_labels=header_labels)
    if to_stdout:
        mock_csv_writer.return_value.write_to_stdout.assert_called_once()
        assert result["report_path"] is None
    else:
        mock_csv_writer.return_value.write_to_file.assert_called_once_with("/report/out")
        assert result["report_path"] == "/report/out/test.csv"
    assert result["error_message"] is None


@pytest.mark.unit
@pytest.mark.parametrize("to_stdout", [False, True])
@patch("reports._shared.output.JsonWriter")
@patch("reports._shared.output.EnvConfig.get_report_out_dir", return_value="/report/out")
def test_write_json_output_destinations(
    mock_env: MagicMock,
    mock_json_writer: MagicMock,
    sample_data: tuple,
    to_stdout: bool,
) -> None:
    """JSON output should support file and stdout destinations."""
    report_prefix, field_names, header_labels, output_data = sample_data
    if not to_stdout:
        mock_json_writer.return_value.write_to_file.return_value = "/report/out/test.json"
    inputs = BaseReportInputs(to_json=True, to_stdout=to_stdout)

    result = write_report_output(
        report_prefix=report_prefix,
        inputs=inputs,
        field_names=field_names,
        header_labels=header_labels,
        output_data=output_data,
    )

    mock_json_writer.assert_called_once_with(name=report_prefix, output_data=output_data)
    if to_stdout:
        mock_json_writer.return_value.write_to_stdout.assert_called_once()
        assert result["report_path"] is None
    else:
        mock_json_writer.return_value.write_to_file.assert_called_once_with("/report/out")
        assert result["report_path"] == "/report/out/test.json"
    assert result["error_message"] is None


@pytest.mark.unit
@patch("reports._shared.output.CsvWriter")
@patch("reports._shared.output.EnvConfig.get_report_out_dir")
def test_write_csv_prefers_inputs_output_dir(
    mock_env: MagicMock, mock_csv_writer: MagicMock, sample_data: tuple
) -> None:
    """inputs.output_dir should override EnvConfig output directory for CSV."""
    report_prefix, field_names, header_labels, output_data = sample_data
    mock_csv_writer.return_value.write_to_file.return_value = "/custom/output/test.csv"
    inputs = BaseReportInputs(to_json=False, to_stdout=False, output_dir="/custom/output")

    result = write_report_output(
        report_prefix=report_prefix,
        inputs=inputs,
        field_names=field_names,
        header_labels=header_labels,
        output_data=output_data,
    )

    mock_env.assert_not_called()
    mock_csv_writer.return_value.write_to_file.assert_called_once_with("/custom/output")
    assert result["report_path"] == "/custom/output/test.csv"


@pytest.mark.unit
@patch("reports._shared.output.JsonWriter")
@patch("reports._shared.output.EnvConfig.get_report_out_dir")
def test_write_json_prefers_inputs_output_dir(
    mock_env: MagicMock, mock_json_writer: MagicMock, sample_data: tuple
) -> None:
    """inputs.output_dir should override EnvConfig output directory for JSON."""
    report_prefix, field_names, header_labels, output_data = sample_data
    mock_json_writer.return_value.write_to_file.return_value = "/custom/output/test.json"
    inputs = BaseReportInputs(to_json=True, to_stdout=False, output_dir="/custom/output")

    result = write_report_output(
        report_prefix=report_prefix,
        inputs=inputs,
        field_names=field_names,
        header_labels=header_labels,
        output_data=output_data,
    )

    mock_env.assert_not_called()
    mock_json_writer.return_value.write_to_file.assert_called_once_with("/custom/output")
    assert result["report_path"] == "/custom/output/test.json"
