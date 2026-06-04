"""Shared output utilities for all report types."""

from typing import Any

from lib.env import EnvConfig
from lib.utils.output.csv_writer import CsvWriter
from lib.utils.output.json_writer import JsonWriter
from reports._shared.input import BaseReportInputs


def write_report_output(
    report_prefix: str,
    inputs: BaseReportInputs,
    field_names: list[str],
    header_labels: list[str],
    output_data: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Write report output to file or stdout in JSON or CSV format.

    Args:
        report_prefix: Prefix for the output filename (e.g., "access_account")
        field_names: List of field names to include in output
        header_labels: List of header labels for CSV output
        output_data: List of dictionaries containing the report data
        to_json: If True, output as JSON instead of CSV
        to_stdout: If True, output to stdout instead of writing to a file

    Returns:
        dict with keys: report_path, error_message, info_message
    """
    report_out_dir = inputs.output_dir if inputs.output_dir else EnvConfig.get_report_out_dir()

    if inputs.to_json:
        json_writer = JsonWriter(name=report_prefix, output_data=output_data)
        if inputs.to_stdout:
            json_writer.write_to_stdout()
            return {"report_path": None, "error_message": None, "info_message": None}
        report_path = json_writer.write_to_file(report_out_dir)
        return {"report_path": report_path, "error_message": None, "info_message": None}

    # CSV output (default)
    csv_writer = CsvWriter(report_prefix, field_names, output_data, header_labels=header_labels)
    if inputs.to_stdout:
        csv_writer.write_to_stdout()
        return {"report_path": None, "error_message": None, "info_message": None}
    report_path = csv_writer.write_to_file(report_out_dir)
    return {"report_path": report_path, "error_message": None, "info_message": None}
