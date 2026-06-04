#!/usr/bin/env python3
"""Create a portable backup archive of the Reporter deployment.

Run from the install directory AFTER stopping all Reporter containers:

    cd /opt/reporter
    docker compose down
    bin/backup /path/to/destination

The archive contains the latest database dump(s) from .backup/ plus the
restore-critical config (.env, docker-compose.yml, .pg-ssl/).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from lib._backup.backup_archive import (
    archive_members,
    dry_run_messages,
    is_backup_dev_mode,
    latest_dump_per_db,
    parse_running_reporter_containers,
    write_archive,
)
from lib._shared.helpers import repo_root

# At runtime this module lives at /opt/reporter/lib/_backup/backup.py.
REPORTER_HOME_DEFAULT = repo_root(Path(__file__))
BACKUP_DIR_ENV = "BACKUP_DIR"
DEFAULT_BACKUP_DIR = ".backup"


def running_reporter_containers() -> list[str]:
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_running_reporter_containers(result.stdout)


def resolve_backup_dir(reporter_home: Path, raw_value: str | None) -> Path:
    if not raw_value:
        return (reporter_home / DEFAULT_BACKUP_DIR).resolve()
    configured = Path(raw_value).expanduser()
    if configured.is_absolute():
        return configured.resolve()
    return (reporter_home / configured).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Reporter backup archive.")
    parser.add_argument("destination", help="Directory where the archive is written.")
    parser.add_argument(
        "--reporter-home",
        default=str(REPORTER_HOME_DEFAULT),
        help="Reporter install directory (default: derived from this script location).",
    )
    args = parser.parse_args()

    reporter_home = Path(args.reporter_home).expanduser().resolve()
    backup_dir = resolve_backup_dir(reporter_home, os.getenv(BACKUP_DIR_ENV))
    destination_dir = Path(args.destination).expanduser().resolve()

    if is_backup_dev_mode():
        dump_files = (
            [path.name for path in backup_dir.glob("*.dump")] if backup_dir.is_dir() else []
        )
        members = archive_members(
            reporter_home,
            backup_dir,
            latest_dump_per_db(dump_files),
        )
        for line in dry_run_messages(backup_dir, members):
            print(line)
        return 0

    running = running_reporter_containers()
    if running:
        print(f"FATAL: Reporter containers are running: {', '.join(running)}", file=sys.stderr)
        print("Stop them first: cd /opt/reporter && docker compose down", file=sys.stderr)
        return 1

    if not backup_dir.is_dir():
        print(f"FATAL: backup directory not found: {backup_dir}", file=sys.stderr)
        return 1

    dump_files = [path.name for path in backup_dir.glob("*.dump")]
    if not dump_files:
        print(f"FATAL: no database dumps found in {backup_dir}", file=sys.stderr)
        return 1

    members = archive_members(reporter_home, backup_dir, latest_dump_per_db(dump_files))

    destination_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    archive_path = destination_dir / f"reporter-backup-{timestamp}.tar.gz"
    write_archive(archive_path, members)
    print(f"Wrote backup archive to {archive_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
