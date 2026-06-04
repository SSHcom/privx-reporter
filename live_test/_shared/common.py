from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from sqlalchemy import text

from lib.clients.postgresql import use_database
import lib.database.db_init as db_init
from live_test._shared.db_env import apply_live_test_db_env

if TYPE_CHECKING:
    from lib.env_sync import SyncConfig, SyncSourceConfig

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
AUDIT_SAMPLE_PATH = SAMPLES_DIR / "audit_event.json"
CONNECTION_SAMPLE_PATH = SAMPLES_DIR / "connection.json"

TEST_DATA_AGE_DAYS = 365 * 5
TEST_RUN_ID_FIELD = "live_test_run_id"

logger = logging.getLogger(__name__)


@dataclass
class LoadTestArgs:
    source: Literal["audit", "connection"]
    records: int
    api_delay_ms: int


@dataclass
class RunMetrics:
    generation_seconds: float = 0.0
    api_wait_seconds: float = 0.0
    db_seconds: float = 0.0


def parse_args() -> LoadTestArgs:
    parser = argparse.ArgumentParser(description="Load test sync_server audit/connection sync paths.")
    parser.add_argument(
        "--source",
        choices=("audit", "connection"),
        required=True,
        help="Sync source implementation to exercise.",
    )
    parser.add_argument(
        "--records",
        type=int,
        required=True,
        help="Number of records to simulate.",
    )
    parser.add_argument(
        "--api-delay-ms",
        type=int,
        default=0,
        help="Artificial API delay per simulated request in milliseconds.",
    )
    parsed = parser.parse_args()

    if parsed.records <= 0:
        parser.error("--records must be greater than 0")
    if parsed.api_delay_ms < 0:
        parser.error("--api-delay-ms cannot be negative")

    return LoadTestArgs(
        source=cast("Literal['audit', 'connection']", parsed.source),
        records=parsed.records,
        api_delay_ms=parsed.api_delay_ms,
    )


def to_iso_z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def base_test_time() -> datetime:
    return datetime.now(UTC) - timedelta(days=TEST_DATA_AGE_DAYS)


def load_sample(sample_path: Path) -> dict[str, Any]:
    with sample_path.open(encoding="utf-8") as handle:
        sample = json.load(handle)
    if not isinstance(sample, dict):
        raise ValueError(f"Sample file must contain one JSON object: {sample_path}")
    return sample


def resolve_source_config(config: SyncConfig, source: str) -> SyncSourceConfig:
    source_config = config.audit_event_config if source == "audit" else config.connection_config
    if source_config is None:
        raise ValueError(
            f"Missing sync configuration for source '{source}'. "
            "Configure SYNC_AUDIT/SYNC_CONNECTION and SYNC_SOURCES in environment variables."
        )
    return source_config


def log_db_targets() -> None:
    """Log resolved admin/data connection targets (same physical DB in live tests)."""
    from lib.env import EnvConfig

    for role, config in EnvConfig.get_db_config().items():
        logger.info(
            "DB target %s: %s@%s:%s/%s ssl=%s",
            role,
            config["user"],
            config["host"],
            config["port"],
            config["name"],
            "on" if config["ssl"] else "off",
        )


def init_data_tables(config: SyncConfig) -> None:
    _ = config
    apply_live_test_db_env()
    log_db_targets()
    db_init.init_databases()


def cleanup_run_data(source: Literal["audit", "connection"], run_id: str) -> int:
    db = use_database("data")
    table_name = "audit_event" if source == "audit" else "connection"
    query = f"DELETE FROM {table_name} WHERE data->>'{TEST_RUN_ID_FIELD}' = :run_id"

    with db.connection.begin():
        result = db.connection.execute(text(query), {"run_id": run_id})

    return int(result.rowcount or 0)
