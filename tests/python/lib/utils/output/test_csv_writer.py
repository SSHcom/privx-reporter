"""Tests for CSV writer class."""

import os
import sys
import tempfile
from io import StringIO

import pytest

from lib.utils.output.csv_writer import CsvWriter


@pytest.mark.integration
def test_csv_writer_basic() -> None:
    """Test basic CSV writing functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        field_names = ["name", "age", "city"]
        output_data = [
            {"name": "Alice", "age": "30", "city": "New York"},
            {"name": "Bob", "age": "25", "city": "London"},
        ]

        writer = CsvWriter("test-file", field_names, output_data)
        file_path = writer.write_to_file(tmpdir)

        # Check that file was created
        assert os.path.exists(file_path)
        assert file_path.endswith(".csv")
        assert "test-file" in file_path

        # Check file contents
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 3  # Header + 2 data rows
            assert "name,age,city" in lines[0]
            assert "Alice,30,New York" in lines[1]
            assert "Bob,25,London" in lines[2]


@pytest.mark.integration
def test_csv_writer_creates_directory() -> None:
    """Test that CSV writer creates directory if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        new_dir = os.path.join(tmpdir, "new", "nested", "directory")
        field_names = ["key", "value"]
        output_data = [{"key": "test", "value": "data"}]

        writer = CsvWriter("test", field_names, output_data)
        file_path = writer.write_to_file(new_dir)

        assert os.path.exists(file_path)
        assert os.path.isdir(new_dir)


@pytest.mark.unit
def test_csv_writer_empty_list_raises_error() -> None:
    """Test that empty output_data list raises ValueError."""
    field_names = ["name", "age"]

    with pytest.raises(ValueError, match="output_data list cannot be empty"):
        CsvWriter("test", field_names, [])


@pytest.mark.unit
def test_csv_writer_mismatched_keys_raises_error() -> None:
    """Test that mismatched keys and field_names raises ValueError."""
    field_names = ["name", "age", "city"]
    output_data = [
        {"name": "Alice", "age": "30"},  # Missing "city" key
    ]

    with pytest.raises(
        ValueError,
        match="First object has .* keys, but field_names has .* items",
    ):
        CsvWriter("test", field_names, output_data)


@pytest.mark.integration
def test_csv_writer_timestamped_filename() -> None:
    """Test that CSV files have timestamped filenames."""
    with tempfile.TemporaryDirectory() as tmpdir:
        field_names = ["id"]
        output_data = [{"id": "1"}]

        writer = CsvWriter("report", field_names, output_data)
        file_path = writer.write_to_file(tmpdir)

        # Check filename format: report.YYYYMMDD_HHMMSS.csv
        filename = os.path.basename(file_path)
        assert filename.startswith("report.")
        assert filename.endswith(".csv")
        # Extract timestamp part
        timestamp_part = filename.replace("report.", "").replace(".csv", "")
        assert len(timestamp_part) == 15  # YYYYMMDD_HHMMSS format
        assert "_" in timestamp_part


@pytest.mark.integration
def test_csv_writer_with_header_labels() -> None:
    """Test CSV writing with custom header labels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        field_names = ["name", "age"]
        header_labels = ["Full Name", "Age (years)"]
        output_data = [
            {"name": "Alice", "age": "30"},
            {"name": "Bob", "age": "25"},
        ]

        writer = CsvWriter("test", field_names, output_data, header_labels)
        file_path = writer.write_to_file(tmpdir)

        # Check file contents
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 3  # Header + 2 data rows
            assert "Full Name,Age (years)" in lines[0]
            assert "Alice,30" in lines[1]
            assert "Bob,25" in lines[2]


@pytest.mark.integration
def test_csv_writer_write_to_stdout() -> None:
    """Test writing CSV data to stdout."""
    field_names = ["id", "value"]
    output_data = [
        {"id": "1", "value": "test"},
        {"id": "2", "value": "data"},
    ]

    writer = CsvWriter("test", field_names, output_data)

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    try:
        writer.write_to_stdout()
        output = captured_output.getvalue()
    finally:
        sys.stdout = old_stdout

    # Check output contains header and data
    lines = output.strip().split("\n")
    assert len(lines) == 3  # Header + 2 data rows
    assert "id,value" in lines[0]
    assert "1,test" in lines[1]
    assert "2,data" in lines[2]


@pytest.mark.integration
def test_csv_writer_write_to_stdout_with_header_labels() -> None:
    """Test writing CSV data to stdout with custom header labels."""
    field_names = ["name", "age"]
    header_labels = ["Full Name", "Age"]
    output_data = [
        {"name": "Alice", "age": "30"},
    ]

    writer = CsvWriter("test", field_names, output_data, header_labels)

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    try:
        writer.write_to_stdout()
        output = captured_output.getvalue()
    finally:
        sys.stdout = old_stdout

    # Check output contains custom header
    lines = output.strip().split("\n")
    assert len(lines) == 2  # Header + 1 data row
    assert "Full Name,Age" in lines[0]
    assert "Alice,30" in lines[1]
