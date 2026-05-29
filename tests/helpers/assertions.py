"""Helper functions for common test assertions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from unittest.mock import MagicMock


def assert_csv_written(
    mock_csv_writer: MagicMock,
    expected_dir: str | None = None,
    expected_filename: str | None = None,
    expected_headers: list[str] | None = None,
    expected_row_count: int | None = None,
    call_count: int = 1,
    csv_writer_module: Any | None = None,  # noqa: ANN401
) -> list[Any]:
    """Assert CSV was written with expected parameters.

    Args:
        mock_csv_writer: The mocked CSV writer instance
        expected_dir: Expected output directory
        expected_filename: Expected filename
        expected_headers: Expected column headers
        expected_row_count: Expected number of rows
        call_count: Expected number of times CsvWriter was instantiated (default: 1)
        csv_writer_module: The module containing CsvWriter class (for new API)

    Returns:
        The data that was written (for further assertions)
    """
    if csv_writer_module is not None:
        # New API: Check CsvWriter class instantiation
        if call_count == 1:
            csv_writer_module.CsvWriter.assert_called_once()
        else:
            assert csv_writer_module.CsvWriter.call_count == call_count

        # Use call_args_list to get all calls, then get the last one
        call_args_list = csv_writer_module.CsvWriter.call_args_list
        assert len(call_args_list) > 0, "CsvWriter should have been called"
        call_args = call_args_list[-1]  # Get the last call
        # CsvWriter is called with positional args: (name, field_names, output_data, header_labels=...)
        # call_args[0] = positional args tuple, call_args[1] = keyword args dict
        assert call_args is not None, "CsvWriter should have been called"
        assert len(call_args) > 0, f"call_args should have positional args, got: {call_args}"
        pos_args = call_args[0]
        assert len(pos_args) >= 3, (
            f"Expected at least 3 positional args (name, field_names, output_data), got {len(pos_args)}: {pos_args}"
        )

        if expected_filename is not None:
            assert pos_args[0] == expected_filename, f"Expected filename {expected_filename}, got {pos_args[0]}"

        if expected_headers is not None:
            assert pos_args[1] == expected_headers, f"Expected headers {expected_headers}, got {pos_args[1]}"

        data = pos_args[2]  # output_data is the third positional argument

        if expected_row_count is not None:
            assert len(data) == expected_row_count, f"Expected {expected_row_count} rows, got {len(data)}"

        # Check write_to_file was called
        if expected_dir is not None:
            mock_csv_writer.write_to_file.assert_called_once_with(expected_dir)

        return data
    else:
        # Old API: Check write_csv function call (for backward compatibility)
        if call_count == 1:
            mock_csv_writer.write_csv.assert_called_once()
        else:
            assert mock_csv_writer.write_csv.call_count == call_count

        call_args = mock_csv_writer.write_csv.call_args

        if expected_dir is not None:
            assert call_args[0][0] == expected_dir, f"Expected dir {expected_dir}, got {call_args[0][0]}"

        if expected_filename is not None:
            assert call_args[0][1] == expected_filename, f"Expected filename {expected_filename}, got {call_args[0][1]}"

        if expected_headers is not None:
            assert call_args[0][2] == expected_headers, f"Expected headers {expected_headers}, got {call_args[0][2]}"

        data = call_args[0][3]

        if expected_row_count is not None:
            assert len(data) == expected_row_count, f"Expected {expected_row_count} rows, got {len(data)}"

        return data


def assert_csv_not_written(mock_csv_writer: MagicMock, csv_writer_module: Any | None = None) -> None:  # noqa: ANN401
    """Assert CSV writer was not called.

    Args:
        mock_csv_writer: The mocked CSV writer instance
        csv_writer_module: The module containing CsvWriter class (for new API)
    """
    if csv_writer_module is not None:
        # New API: Check CsvWriter class was not instantiated
        csv_writer_module.CsvWriter.assert_not_called()
    else:
        # Old API: Check write_csv function was not called
        mock_csv_writer.write_csv.assert_not_called()


def assert_api_called_with_pagination(
    mock_api_method: MagicMock,
    mock_api: MagicMock,
    expected_calls: int,
    **expected_kwargs: Any,  # noqa: ANN401
) -> None:
    """Assert API method was called the expected number of times with pagination.

    Args:
        mock_api_method: The mocked API method
        mock_api: The API object passed to the method
        expected_calls: Expected number of calls
        **expected_kwargs: Expected keyword arguments in each call
    """
    assert mock_api_method.call_count == expected_calls

    for call in mock_api_method.call_args_list:
        assert call[0][0] == mock_api
        for key, value in expected_kwargs.items():
            if key in call[1]:
                assert call[1][key] == value


def get_csv_data(mock_csv_writer: MagicMock, csv_writer_module: Any | None = None) -> list[Any]:  # noqa: ANN401
    """Extract the data that was written to CSV.

    Args:
        mock_csv_writer: The mocked CSV writer instance
        csv_writer_module: The module containing CsvWriter class (for new API)

    Returns:
        The data that was written
    """
    if csv_writer_module is not None:
        # New API: Get data from CsvWriter class instantiation (third positional arg)
        call_args = csv_writer_module.CsvWriter.call_args
        return call_args[0][2] if call_args and len(call_args[0]) > 2 else []
    else:
        # Old API: Get data from write_csv function call
        call_args = mock_csv_writer.write_csv.call_args
        return call_args[0][3] if call_args else []


def get_csv_headers(mock_csv_writer: MagicMock, csv_writer_module: Any | None = None) -> list[str]:  # noqa: ANN401
    """Extract the headers that were written to CSV.

    Args:
        mock_csv_writer: The mocked CSV writer instance
        csv_writer_module: The module containing CsvWriter class (for new API)

    Returns:
        The headers that were written
    """
    if csv_writer_module is not None:
        # New API: Get headers from CsvWriter class instantiation (second positional arg)
        call_args = csv_writer_module.CsvWriter.call_args
        return call_args[0][1] if call_args and len(call_args[0]) > 1 else []
    else:
        # Old API: Get headers from write_csv function call
        call_args = mock_csv_writer.write_csv.call_args
        return call_args[0][2] if call_args else []
