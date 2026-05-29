"""Database dump helpers for the backup service.

Pure helpers (target resolution, filename, command, rotation) are unit-tested.
`run_dump_cycle` is a thin subprocess wrapper and is not unit-tested.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING
from datetime import UTC, datetime
from pathlib import Path

if TYPE_CHECKING:
    from collections.abc import Mapping

    from lib.env_backup import BackupConfig

logger = logging.getLogger(__name__)

ADMIN_LABEL = "admin"
DATA_LABEL = "data"


@dataclass(frozen=True)
class DatabaseTarget:
    label: str
    host: str
    port: str
    name: str
    user: str
    password: str
    sslmode: str


def pgsslmode_for(ssl_mode: str) -> str:
    """Map the DB_*_SSL_MODE on/off flag to a libpq sslmode value."""
    return "require" if ssl_mode.strip().lower() == "on" else "disable"


def databases_for_target(target: str, env: Mapping[str, str]) -> list[DatabaseTarget]:
    """Resolve the backup target into the concrete databases to dump."""
    if target == ADMIN_LABEL:
        labels = [ADMIN_LABEL]
    elif target == DATA_LABEL:
        labels = [DATA_LABEL]
    else:
        labels = [ADMIN_LABEL, DATA_LABEL]

    targets: list[DatabaseTarget] = []
    for label in labels:
        prefix = "DB_ADMIN_" if label == ADMIN_LABEL else "DB_DATA_"
        targets.append(
            DatabaseTarget(
                label=label,
                host=env[f"{prefix}HOST"],
                port=env.get(f"{prefix}PORT", "5432"),
                name=env[f"{prefix}NAME"],
                user=env[f"{prefix}USER"],
                password=env.get(f"{prefix}PASSWORD", ""),
                sslmode=pgsslmode_for(env.get(f"{prefix}SSL_MODE", "off")),
            )
        )
    return targets


def dump_filename(label: str, now: datetime) -> str:
    """Build a UTC, lexically-sortable dump filename for a database label."""
    timestamp = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{label}-{timestamp}.dump"


def build_pg_dump_command(target: DatabaseTarget, output_path: Path) -> list[str]:
    """Build the pg_dump argv for a custom-format (-Fc) dump."""
    return [
        "pg_dump",
        "-h", target.host,
        "-p", str(target.port),
        "-U", target.user,
        "-d", target.name,
        "-Fc",
        "-f", str(output_path),
    ]


def snapshots_to_prune(existing: list[str], snapshots: int) -> list[str]:
    """Return the oldest dump filenames to delete so only `snapshots` remain.

    Filenames sort chronologically thanks to the ISO-like UTC timestamp.
    """
    ordered = sorted(existing)
    if len(ordered) <= snapshots:
        return []
    return ordered[: len(ordered) - snapshots]


def run_dump_cycle(
    config: BackupConfig,
    backup_dir: str | Path,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> None:
    """Dump every targeted database and prune old snapshots. Thin subprocess wrapper."""
    env = os.environ if env is None else env
    now = datetime.now(UTC) if now is None else now
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)

    for target in databases_for_target(config.target, env):
        output_path = backup_path / dump_filename(target.label, now)
        run_env = dict(env)
        run_env["PGPASSWORD"] = target.password
        run_env["PGSSLMODE"] = target.sslmode
        logger.info("Dumping %s database to %s", target.label, output_path)
        subprocess.run(build_pg_dump_command(target, output_path), check=True, env=run_env)

        existing = [p.name for p in backup_path.glob(f"{target.label}-*.dump")]
        for stale in snapshots_to_prune(existing, config.snapshots):
            (backup_path / stale).unlink(missing_ok=True)
            logger.info("Pruned old snapshot %s", stale)
