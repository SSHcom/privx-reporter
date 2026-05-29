import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Table, func, select

from lib.clients.postgresql import use_database

logger = logging.getLogger(__name__)


def get_latest_timestamp(table: Table) -> datetime | None:
    """
    Get the latest timestamp from a database table.

    Args:
        table: SQLAlchemy table with a 'timestamp' column

    Returns:
        The latest timestamp as timezone-aware datetime, or None if no data
    """
    db = use_database("data")

    with db.connection.begin():
        result = db.connection.execute(select(func.max(table.c.timestamp))).scalar()

    latest_timestamp = result

    if latest_timestamp and latest_timestamp.tzinfo is None:
        latest_timestamp = latest_timestamp.replace(tzinfo=UTC)

    return latest_timestamp


def calculate_time_range(
    latest_timestamp: datetime | None,
    range_minutes: int,
    max_range_hours: int | None = None,
) -> tuple[datetime, datetime]:
    """
    Calculate start and end time range for syncing.

    Args:
        latest_timestamp: The latest synced timestamp, or None if no data
        range_minutes: Number of minutes to look back if no latest_timestamp
        max_range_hours: Optional maximum allowed sync range in hours

    Returns:
        Tuple of (start_time, end_time) as timezone-aware datetimes
    """
    end_time = datetime.now(UTC)

    if latest_timestamp:
        start_time = latest_timestamp
        logger.info(f"Latest synced timestamp: {start_time}")
    else:
        start_time = end_time - timedelta(minutes=range_minutes)
        logger.info(
            "No previous data found, using range_minutes=%s (start=%s, end=%s)",
            range_minutes,
            start_time,
            end_time,
        )

    if max_range_hours is not None:
        max_start_time = end_time - timedelta(hours=max_range_hours)
        if start_time < max_start_time:
            logger.info(
                "Clamping sync start time to max range (%s hours). Original start: %s, clamped start: %s",
                max_range_hours,
                start_time,
                max_start_time,
            )
            start_time = max_start_time

    return start_time, end_time


def calculate_backfill_range(
    days: int | None = None,
    from_date: datetime | None = None,
) -> tuple[datetime, datetime]:
    """
    Calculate start and end time range for backfill operation.

    Args:
        days: Number of days to look back from now
        from_date: Specific start date (syncs from this date until now)

    Returns:
        Tuple of (start_time, end_time) as timezone-aware datetimes

    Raises:
        ValueError: If neither days nor from_date is provided, or both are provided
    """
    if days is None and from_date is None:
        raise ValueError("Either 'days' or 'from_date' must be provided")
    if days is not None and from_date is not None:
        raise ValueError("Cannot specify both 'days' and 'from_date'")

    end_time = datetime.now(UTC)

    if days is not None:
        start_time = end_time - timedelta(days=days)
    else:
        assert from_date is not None
        if from_date.tzinfo is None:
            start_time = from_date.replace(tzinfo=UTC)
        else:
            start_time = from_date

    return start_time, end_time


def build_timestamped_rows(
    items: list[dict[str, Any]],
    latest_timestamp: datetime | None,
    timestamp_key: str = "created",
) -> list[dict[str, Any]]:
    """
    Build database rows from items with timestamps, filtering out old items.

    Args:
        items: List of items with timestamp data
        latest_timestamp: The latest synced timestamp, or None if no data
        timestamp_key: The key in each item containing the timestamp string

    Returns:
        List of row dictionaries with 'timestamp' and 'data' keys
    """
    rows = []

    for item in items:
        row = build_timestamped_row(item, latest_timestamp, timestamp_key)
        if row is not None:
            rows.append(row)

    return rows


def build_timestamped_row(
    item: dict[str, Any],
    latest_timestamp: datetime | None,
    timestamp_key: str = "created",
) -> dict[str, Any] | None:
    """
    Build a database row from a single item with timestamp filtering.

    Args:
        item: Item with timestamp data
        latest_timestamp: The latest synced timestamp, or None if no data
        timestamp_key: The key in the item containing the timestamp string

    Returns:
        Row dictionary with 'timestamp' and 'data' keys, or None if item is old
    """
    item_timestamp = datetime.fromisoformat(item[timestamp_key].replace("Z", "+00:00"))

    if latest_timestamp and item_timestamp < latest_timestamp:
        return None

    return {"timestamp": item_timestamp, "data": item}
