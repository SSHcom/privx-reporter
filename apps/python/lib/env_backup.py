"""Backup service environment variable configuration and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lib.service.env_source import getEnv

BACKUP_CONFIG = "BACKUP_CONFIG"
BACKUP_DIR = "BACKUP_DIR"
BACKUP_DIR_BASENAME = "REPORTER-BACKUP"
DEFAULT_BACKUP_CONFIG = "false,all,720,5"

ENABLED_VALUES = {"true", "false"}
TARGET_VALUES = {"admin", "data", "all"}
INTERVAL_MINUTES_MIN = 60
SNAPSHOTS_MIN = 1


def default_backup_dir() -> str:
    """Return the default backup directory under the current user's home directory."""
    return str(Path.home() / BACKUP_DIR_BASENAME)


@dataclass(frozen=True)
class BackupConfig:
    enabled: bool
    target: str
    interval_minutes: int
    snapshots: int


def parse_backup_config(raw_value: str | None = None) -> BackupConfig:
    """Parse a BACKUP_CONFIG string into a typed config, raising ValueError on bad input."""
    if raw_value is None:
        raw_value = getEnv(BACKUP_CONFIG, DEFAULT_BACKUP_CONFIG)

    parts = [part.strip() for part in raw_value.split(",")]
    if len(parts) != 4:
        raise ValueError(f"{BACKUP_CONFIG} must be '<enabled>,<target>,<interval-minutes>,<snapshots>'")

    enabled_raw, target, interval_raw, snapshots_raw = parts

    if enabled_raw not in ENABLED_VALUES:
        raise ValueError(f"{BACKUP_CONFIG}: enabled must be 'true' or 'false'")
    if target not in TARGET_VALUES:
        raise ValueError(f"{BACKUP_CONFIG}: target must be one of 'admin', 'data', 'all'")

    if not interval_raw.isdigit():
        raise ValueError(f"{BACKUP_CONFIG}: interval-minutes must be numeric")
    interval_minutes = int(interval_raw)
    if interval_minutes < INTERVAL_MINUTES_MIN:
        raise ValueError(f"{BACKUP_CONFIG}: interval-minutes must be at least {INTERVAL_MINUTES_MIN}")

    if not snapshots_raw.isdigit():
        raise ValueError(f"{BACKUP_CONFIG}: snapshots must be numeric")
    snapshots = int(snapshots_raw)
    if snapshots < SNAPSHOTS_MIN:
        raise ValueError(f"{BACKUP_CONFIG}: snapshots must be at least {SNAPSHOTS_MIN}")

    return BackupConfig(
        enabled=enabled_raw == "true",
        target=target,
        interval_minutes=interval_minutes,
        snapshots=snapshots,
    )
