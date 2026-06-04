"""Tests for JSON writer class."""

import json
import os
import sys
import tempfile
from io import StringIO

import pytest

from lib.utils.output.json_writer import JsonWriter


@pytest.mark.integration
def test_json_writer_basic() -> None:
    """Test basic JSON writing functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_data = [
            {"name": "Alice", "age": 30, "city": "New York"},
            {"name": "Bob", "age": 25, "city": "London"},
        ]

        writer = JsonWriter("test-file", output_data)
        file_path = writer.write_to_file(tmpdir)

        # Check that file was created
        assert os.path.exists(file_path)
        assert file_path.endswith(".json")
        assert "test-file" in file_path

        # Check file contents
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
            assert len(data) == 2
            assert data[0]["name"] == "Alice"
            assert data[0]["age"] == 30
            assert data[1]["name"] == "Bob"
            assert data[1]["age"] == 25


@pytest.mark.integration
def test_json_writer_creates_directory() -> None:
    """Test that JSON writer creates directory if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        new_dir = os.path.join(tmpdir, "new", "nested", "directory")
        output_data = [{"key": "test", "value": "data"}]

        writer = JsonWriter("test", output_data)
        file_path = writer.write_to_file(new_dir)

        assert os.path.exists(file_path)
        assert os.path.isdir(new_dir)


@pytest.mark.unit
def test_json_writer_empty_list_raises_error() -> None:
    """Test that empty output_data list raises ValueError."""
    with pytest.raises(ValueError, match="output_data list cannot be empty"):
        JsonWriter("test", [])


@pytest.mark.integration
def test_json_writer_timestamped_filename() -> None:
    """Test that JSON files have timestamped filenames."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_data = [{"id": "1"}]

        writer = JsonWriter("report", output_data)
        file_path = writer.write_to_file(tmpdir)

        # Check filename format: report.YYYYMMDD_HHMMSS.json
        filename = os.path.basename(file_path)
        assert filename.startswith("report.")
        assert filename.endswith(".json")
        # Extract timestamp part
        timestamp_part = filename.replace("report.", "").replace(".json", "")
        assert len(timestamp_part) == 15  # YYYYMMDD_HHMMSS format
        assert "_" in timestamp_part


@pytest.mark.integration
def test_json_writer_custom_indent() -> None:
    """Test JSON writing with custom indentation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_data = [{"key": "value", "nested": {"a": 1, "b": 2}}]

        writer = JsonWriter("test", output_data, indent=4)
        file_path = writer.write_to_file(tmpdir)

        # Check file contents have 4-space indentation
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            # Check that nested content is indented with 4 spaces
            lines = content.split("\n")
            # Find the line with "nested" key
            nested_line = [line for line in lines if '"nested"' in line][0]
            # Should have 4 spaces of indentation (2 levels * 2 spaces base + 4 custom indent)
            assert nested_line.startswith("        ")  # 8 spaces total


@pytest.mark.integration
def test_json_writer_write_to_stdout() -> None:
    """Test writing JSON data to stdout."""
    output_data = [
        {"id": "1", "value": "test"},
        {"id": "2", "value": "data"},
    ]

    writer = JsonWriter("test", output_data)

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    try:
        writer.write_to_stdout()
        output = captured_output.getvalue()
    finally:
        sys.stdout = old_stdout

    # Check output is valid JSON
    data = json.loads(output.strip())
    assert len(data) == 2
    assert data[0]["id"] == "1"
    assert data[1]["id"] == "2"


@pytest.mark.integration
def test_json_writer_write_to_stdout_with_indent() -> None:
    """Test writing JSON data to stdout with custom indentation."""
    output_data = [{"key": "value"}]

    writer = JsonWriter("test", output_data, indent=4)

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    try:
        writer.write_to_stdout()
        output = captured_output.getvalue()
    finally:
        sys.stdout = old_stdout

    # Check output is valid JSON and ends with newline
    assert output.endswith("\n")
    data = json.loads(output.strip())
    assert data[0]["key"] == "value"


@pytest.mark.integration
def test_json_writer_unicode_characters() -> None:
    """Test JSON writing with unicode characters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_data = [
            {"name": "José", "city": "São Paulo", "emoji": "🚀"},
        ]

        writer = JsonWriter("test", output_data)
        file_path = writer.write_to_file(tmpdir)

        # Check file contents preserve unicode
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
            assert data[0]["name"] == "José"
            assert data[0]["city"] == "São Paulo"
            assert data[0]["emoji"] == "🚀"


@pytest.mark.integration
def test_json_writer_complex_nested_structure() -> None:
    """Test JSON writing with complex nested structures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_data = [
            {
                "id": 1,
                "metadata": {
                    "tags": ["important", "urgent"],
                    "author": {"name": "Alice", "email": "alice@example.com"},
                },
                "items": [{"name": "item1", "count": 5}, {"name": "item2", "count": 3}],
            }
        ]

        writer = JsonWriter("test", output_data)
        file_path = writer.write_to_file(tmpdir)

        # Check file contents
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
            assert data[0]["id"] == 1
            assert len(data[0]["metadata"]["tags"]) == 2
            assert data[0]["metadata"]["author"]["name"] == "Alice"
            assert len(data[0]["items"]) == 2
            assert data[0]["items"][0]["count"] == 5
