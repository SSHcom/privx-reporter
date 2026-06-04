import csv
from pathlib import Path


def _get_enabled_events_csv_path() -> Path:
    return Path(__file__).resolve().parents[2] / "events_enabled.csv"


def read_fixed_event_codes() -> set[int]:
    """Read fixed event codes from administration/events_enabled.csv."""
    path = _get_enabled_events_csv_path()
    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return {int(event_type["CODE"]) for event_type in reader}
