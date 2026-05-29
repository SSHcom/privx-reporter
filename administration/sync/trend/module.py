import argparse
import logging
from typing import Any

from lib.database import init_databases
from lib.database.sync.trend import DEFAULT_TREND_DAYS, run_trend_sync

logger = logging.getLogger(__name__)


def _parse_days(days_value: object) -> int:
    days = int(days_value) if days_value is not None else DEFAULT_TREND_DAYS
    if days <= 0:
        raise ValueError("--days must be a positive integer.")
    return days


def handle_trend_sync(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, str | None]:
    """Backfill trend rows from local sync database."""
    _ = config

    try:
        days = _parse_days(getattr(args, "days", None))
        init_databases()
        summary = run_trend_sync(days=days)
    except Exception as exc:
        logger.error("Trend sync failed: %s", exc, exc_info=True)
        return {"error_message": f"Trend sync failed: {exc}", "info_message": None}

    return {
        "error_message": None,
        "info_message": (
            f"Filled {summary.placeholder_rows} placeholder rows for past {summary.days} day(s); "
            f"today inserted: {summary.today_inserted}."
        ),
    }
