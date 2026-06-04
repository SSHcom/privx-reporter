"""CSV writer module for creating timestamped CSV files from JSON objects."""

import csv
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CsvWriter:
    """A class for writing CSV data to files or stdout."""

    def __init__(
        self,
        name: str,
        field_names: list[str],
        output_data: list[dict[str, Any]],
        header_labels: list[str] | None = None,
    ) -> None:
        """
        Initialize a CSV writer.

        Args:
            name: Base name for the file (without extension)
            field_names: List of column headers (fieldnames for DictWriter)
            output_data: List of JSON objects (dictionaries) to write
            header_labels: Optional list of human-readable header labels. If provided,
                          these will be used for the CSV header row instead of field_names.

        Raises:
            ValueError: If output_data is empty or if the first object has a different
                       number of keys than the field_names length
        """
        if not output_data:
            raise ValueError("output_data list cannot be empty")

        # Validate that the first object has the same number of keys as field_names
        first_object = output_data[0]
        first_object_keys = len(first_object.keys())

        if first_object_keys != len(field_names):
            raise ValueError(
                f"First object has {first_object_keys} keys, but field_names has "
                f"{len(field_names)} items. They must match."
            )

        self.name = name
        self.field_names = field_names
        self.output_data = output_data
        self.header_labels = header_labels

    def write_to_file(self, dir_path: str) -> str:
        """
        Write CSV data to a timestamped file.

        Args:
            dir_path: Directory path where the CSV file will be created

        Returns:
            str: Path to the created CSV file
        """
        # Create directory if it doesn't exist
        Path(dir_path).mkdir(parents=True, exist_ok=True)

        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.name}.{timestamp}.csv"
        file_path = os.path.join(dir_path, filename)

        # Write CSV file
        logger.info(f"Writing CSV file to {file_path} ...")
        with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.field_names)

            if self.header_labels:
                # Use custom header labels
                writer.writerow(dict(zip(self.field_names, self.header_labels)))
            else:
                # Use fieldnames as headers
                writer.writeheader()

            writer.writerows(self.output_data)

        return file_path

    def write_to_stdout(self) -> None:
        """Write CSV data to stdout."""
        writer = csv.DictWriter(sys.stdout, fieldnames=self.field_names)

        if self.header_labels:
            # Use custom header labels
            writer.writerow(dict(zip(self.field_names, self.header_labels)))
        else:
            # Use fieldnames as headers
            writer.writeheader()

        writer.writerows(self.output_data)
