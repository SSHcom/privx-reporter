"""Sync server environment variables configuration and validation."""

import logging
import os
from dataclasses import dataclass

# Available sources
SYNC_SOURCES = "SYNC_SOURCES"

# Source names
AUDIT_EVENT_SOURCE = "audit"
CONNECTION_SOURCE = "connection"
TREND_SOURCE = "trends"
CONCURRENT_SOURCE = "concurrent"

# Source configurations
SYNC_AUDIT = "SYNC_AUDIT"
SYNC_CONNECTION = "SYNC_CONNECTION"

# Other environment variables
SYNC_BATCH_SIZE = "SYNC_BATCH_SIZE"
SYNC_MAX_RANGE_HOURS = "SYNC_MAX_RANGE_HOURS"
SYNC_WINDOW_SIZES_MINUTES = "SYNC_WINDOW_SIZES_MINUTES"
SYNC_MAX_RECORDS_PER_WINDOW = "SYNC_MAX_RECORDS_PER_WINDOW"
SYNC_WINDOW_SIZE_DOWN_MINUTES = "SYNC_WINDOW_SIZE_DOWN_MINUTES"
SYNC_TREND_HOUR = "SYNC_TREND_HOUR"

# Misc
DEFAULT_SYNC_CONFIG = "60,70,15"
DEFAULT_SYNC_WINDOW_SIZES_MINUTES = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
DEFAULT_SYNC_WINDOW_SIZE_DOWN_MINUTES = 2
DEFAULT_SYNC_MAX_RECORDS_PER_WINDOW = 30_000


@dataclass
class SyncSourceConfig:
    source: str
    minutes: int
    range_minutes: int
    retention_days: int


@dataclass
class SyncConfigValues:
    sources: list[str]
    batch_size: int
    max_range_hours: int
    window_sizes_minutes: list[int]
    max_records_per_window: int
    window_size_down_minutes: int
    sync_trend_hour: int | None
    connection_config: SyncSourceConfig | None
    audit_event_config: SyncSourceConfig | None


logger = logging.getLogger(__name__)


def parse_retention_days(env_var: str, default: str = DEFAULT_SYNC_CONFIG) -> int:
    raw_value = os.getenv(env_var, default)
    parts = [part.strip() for part in raw_value.split(",")]

    if len(parts) != 3:
        msg = f"{env_var} must contain exactly 3 comma-separated numbers (minutes,range_minutes,retention_days)"
        raise ValueError(msg)

    try:
        retention_days = int(parts[2])
    except ValueError as error:
        raise ValueError(f"{env_var} must contain only integer values") from error

    if retention_days <= 0:
        raise ValueError(f"{env_var}: retention_days must be > 0")

    return retention_days


class SyncConfig:
    """Sync server configuration."""

    sources: list[str] = []
    batch_size: int = 500
    max_range_hours: int = 2191
    window_sizes_minutes: list[int] = DEFAULT_SYNC_WINDOW_SIZES_MINUTES
    max_records_per_window: int = DEFAULT_SYNC_MAX_RECORDS_PER_WINDOW
    window_size_down_minutes: int = DEFAULT_SYNC_WINDOW_SIZE_DOWN_MINUTES
    sync_trend_hour: int | None = None
    connection_config: SyncSourceConfig | None = None
    audit_event_config: SyncSourceConfig | None = None

    def __init__(self) -> None:
        self.sources = [source.strip() for source in os.getenv(SYNC_SOURCES, "").split(",") if source.strip()]
        self.batch_size = int(os.getenv(SYNC_BATCH_SIZE, self.batch_size))
        self.max_range_hours = int(os.getenv(SYNC_MAX_RANGE_HOURS, self.max_range_hours))
        self.window_sizes_minutes = self._parse_window_sizes(
            os.getenv(SYNC_WINDOW_SIZES_MINUTES),
            default=self.window_sizes_minutes,
        )
        self.max_records_per_window = int(os.getenv(SYNC_MAX_RECORDS_PER_WINDOW, self.max_records_per_window))
        self.window_size_down_minutes = int(
            os.getenv(SYNC_WINDOW_SIZE_DOWN_MINUTES, self.window_size_down_minutes),
        )
        self.sync_trend_hour = self._parse_sync_trend_hour(os.getenv(SYNC_TREND_HOUR))
        self.connection_config = self._parse_sync_config(CONNECTION_SOURCE, SYNC_CONNECTION)
        self.audit_event_config = self._parse_sync_config(AUDIT_EVENT_SOURCE, SYNC_AUDIT)
        self._validate()

    def get_config_values(self) -> SyncConfigValues:
        return SyncConfigValues(
            sources=self.sources,
            batch_size=self.batch_size,
            max_range_hours=self.max_range_hours,
            window_sizes_minutes=self.window_sizes_minutes,
            max_records_per_window=self.max_records_per_window,
            window_size_down_minutes=self.window_size_down_minutes,
            sync_trend_hour=self.sync_trend_hour,
            connection_config=self.connection_config,
            audit_event_config=self.audit_event_config,
        )

    def log_config_values(self) -> None:
        logger.info(f"--- Sync sources: {self.sources}")
        logger.info(f"--- Sync batch size: {self.batch_size}")
        logger.info(f"--- Sync max range: {self.max_range_hours} hours")
        logger.info(f"--- Sync window sizes (min): {self.window_sizes_minutes}")
        logger.info(f"--- Sync max records per window: {self.max_records_per_window}")
        logger.info(f"--- Sync window down-step size (min): {self.window_size_down_minutes}")
        logger.info(
            f"--- Sync trend daily hour (UTC): "
            f"{self.sync_trend_hour if self.sync_trend_hour is not None else 'disabled'}"
        )

        audit_event_config = self.audit_event_config
        if AUDIT_EVENT_SOURCE in self.sources:
            assert audit_event_config is not None
            logger.info(f"--- Audit sync interval: {audit_event_config.minutes} minutes")
            logger.info(f"--- Audit sync range: {audit_event_config.range_minutes} minutes")
            logger.info(f"--- Audit data retention: {audit_event_config.retention_days} days")

        connection_config = self.connection_config
        if CONNECTION_SOURCE in self.sources:
            assert connection_config is not None
            logger.info(f"--- Connection sync interval: {connection_config.minutes} minutes")
            logger.info(f"--- Connection sync range: {connection_config.range_minutes} minutes")
            logger.info(f"--- Connection data retention: {connection_config.retention_days} days")

    def _parse_sync_config(self, source: str, env_var: str, default: str = DEFAULT_SYNC_CONFIG) -> SyncSourceConfig:
        raw_value = os.getenv(env_var, default)
        parts = [part.strip() for part in raw_value.split(",")]

        if len(parts) != 3:
            msg = f"{env_var} must contain exactly 3 comma-separated numbers (minutes,range_minutes,retention_days)"
            raise ValueError(msg)

        try:
            minutes = int(parts[0])
            range_minutes = int(parts[1])
            retention_days = int(parts[2])
        except ValueError as error:
            raise ValueError(f"{env_var} must contain only integer values") from error

        return SyncSourceConfig(
            source=source,
            minutes=minutes,
            range_minutes=range_minutes,
            retention_days=retention_days,
        )

    def _parse_window_sizes(self, raw_value: str | None, default: list[int]) -> list[int]:
        if raw_value is None:
            return default.copy()

        parts = [part.strip() for part in raw_value.split(",") if part.strip()]
        if len(parts) == 0:
            raise ValueError(f"{SYNC_WINDOW_SIZES_MINUTES} must contain at least one integer value")

        try:
            return [int(part) for part in parts]
        except ValueError as error:
            raise ValueError(f"{SYNC_WINDOW_SIZES_MINUTES} must contain only integer values") from error

    def _parse_sync_trend_hour(self, raw_value: str | None) -> int | None:
        if raw_value is None or raw_value.strip() == "":
            return None

        try:
            return int(raw_value.strip())
        except ValueError as error:
            raise ValueError(f"{SYNC_TREND_HOUR} must be an integer in range 0..23") from error

    def _validate(self) -> None:
        if not self.sources:
            raise ValueError(f"{SYNC_SOURCES} must be a comma-separated list of sources")

        if len(self.sources) == 0:
            raise ValueError(f"{SYNC_SOURCES} must contain at least one source")

        if self.batch_size <= 0:
            raise ValueError(f"{SYNC_BATCH_SIZE} must be a positive integer")
        if self.max_range_hours <= 0:
            raise ValueError(f"{SYNC_MAX_RANGE_HOURS} must be a positive integer")
        if self.max_records_per_window <= 0:
            raise ValueError(f"{SYNC_MAX_RECORDS_PER_WINDOW} must be a positive integer")
        if self.window_size_down_minutes <= 0:
            raise ValueError(f"{SYNC_WINDOW_SIZE_DOWN_MINUTES} must be a positive integer")
        if self.sync_trend_hour is not None and not (0 <= self.sync_trend_hour <= 23):
            raise ValueError(f"{SYNC_TREND_HOUR} must be in range 0..23")
        if len(self.window_sizes_minutes) == 0:
            raise ValueError(f"{SYNC_WINDOW_SIZES_MINUTES} must contain at least one integer value")
        if any(size <= 0 for size in self.window_sizes_minutes):
            raise ValueError(f"{SYNC_WINDOW_SIZES_MINUTES} must contain only positive integers")

        if self.connection_config:
            self._validate_sync_config(self.connection_config)

        if self.audit_event_config:
            self._validate_sync_config(self.audit_event_config)

    def _validate_sync_config(self, sync_config: SyncSourceConfig) -> None:
        if sync_config.minutes <= 0:
            raise ValueError(f"{sync_config.source}: minutes must be > 0")

        if sync_config.range_minutes <= 0:
            raise ValueError(f"{sync_config.source}: range_minutes must be > 0")

        if sync_config.retention_days <= 0:
            raise ValueError(f"{sync_config.source}: retention_days must be > 0")
