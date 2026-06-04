"""JSON writer module for creating JSON output from data objects."""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class JsonWriter:
    """A class for writing JSON data to files or stdout."""

    def __init__(
        self,
        name: str,
        output_data: list[dict[str, Any]],
        indent: int = 2,
    ) -> None:
        """
        Initialize a JSON writer.

        Args:
            name: Base name for the file (without extension)
            output_data: List of JSON objects (dictionaries) to write
            indent: JSON indentation level (default: 2)

        Raises:
            ValueError: If output_data is empty
        """
        if not output_data:
            raise ValueError("output_data list cannot be empty")

        self.name = name
        self.output_data = output_data
        self.indent = indent

    def write_to_file(self, dir_path: str) -> str:
        """
        Write JSON data to a timestamped file.

        Args:
            dir_path: Directory path where the JSON file will be created

        Returns:
            str: Path to the created JSON file
        """
        # Create directory if it doesn't exist
        Path(dir_path).mkdir(parents=True, exist_ok=True)

        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.name}.{timestamp}.json"
        file_path = os.path.join(dir_path, filename)

        # Write JSON file
        logger.info(f"Writing JSON file to {file_path} ...")
        with open(file_path, "w", encoding="utf-8") as jsonfile:
            json.dump(self.output_data, jsonfile, indent=self.indent, ensure_ascii=False)

        return file_path

    def write_to_stdout(self) -> None:
        """Write JSON data to stdout."""
        json.dump(self.output_data, sys.stdout, indent=self.indent, ensure_ascii=False)
        sys.stdout.write("\n")
