"""Pure helpers for the host-side backup archive script."""

from __future__ import annotations

import tarfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

# Compose container names that must be stopped before archiving.
REPORTER_CONTAINER_NAMES = (
    "reporter-sync",
    "reporter-ui",
    "reporter-data-db",
    "reporter-admin-db",
    "reporter-backup",
)

# Restore-critical files/dirs (relative to the reporter home), beyond DB dumps.
CONFIG_MEMBERS = (
    "Dockerfile-backup",
    "administration",
    "backup_server",
    "bin",
    "docker-compose.yml",
    "lib",
    "pyproject.toml",
    "reports",
    "uv.lock",
    ".env",
    ".pg-ssl",
    ".env-example",
    ".info",
)


def parse_running_reporter_containers(
    docker_ps_output: str,
    known: Iterable[str] = REPORTER_CONTAINER_NAMES,
) -> list[str]:
    """Return the known Reporter container names present in `docker ps` output."""
    running = {line.strip() for line in docker_ps_output.splitlines() if line.strip()}
    return [name for name in known if name in running]


def latest_dump_per_db(dump_files: Iterable[str]) -> dict[str, str]:
    """Pick the newest dump filename per database label (sorts chronologically)."""
    latest: dict[str, str] = {}
    for filename in sorted(dump_files):
        label = filename.split("-", 1)[0]
        latest[label] = filename
    return latest


def archive_members(
    reporter_home: Path,
    backup_dir: Path,
    latest_dumps: Mapping[str, str],
) -> list[tuple[Path, str]]:
    """Build (source_path, archive_name) pairs: latest dumps + existing config."""
    members: list[tuple[Path, str]] = []
    for filename in latest_dumps.values():
        members.append((backup_dir / filename, f".backup/{filename}"))
    for relative in CONFIG_MEMBERS:
        source = reporter_home / relative
        if source.exists():
            members.append((source, relative))
    return members


def write_archive(destination: Path, members: list[tuple[Path, str]]) -> None:
    """Write a gzip-compressed tar archive containing the given members."""
    with tarfile.open(destination, "w:gz") as tar:
        for source, arcname in members:
            tar.add(source, arcname=arcname)
