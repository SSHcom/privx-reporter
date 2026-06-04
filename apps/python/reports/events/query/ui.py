"""UI list handlers for events/query report options."""

import csv
from pathlib import Path

from lib._report.generator import UIListResponse

EVENTS_ENABLED_CSV = Path(__file__).resolve().parents[3] / "administration" / "events_enabled.csv"


def get_event_names() -> list[str]:
    """Return event names from the first column of events_enabled.csv."""
    with EVENTS_ENABLED_CSV.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)
        next(reader, None)  # Skip header row.
        return [row[0] for row in reader if row and row[0].strip()]


def get_list(list_key: str) -> UIListResponse:
    """Retrieve UI list values for events/query reports."""
    if list_key == "event_names":
        return UIListResponse(values=get_event_names())

    return UIListResponse(
        values=[],
        error_message=f"Unknown list key: '{list_key}'",
    )
