"""Pure helpers for the host-side backup archive script."""

from __future__ import annotations

import os
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

# Set by apps/python/lib/_backup/run (bin/backup). Production release/common/bin/backup does not set it.
BACKUP_DEV_MODE_ENV = "REPORTER_BACKUP_DEV_MODE"
BACKUP_DEV_MODE_TRUTHY = frozenset({"1", "true", "yes"})

# Production install path; used in dev dry-run messaging instead of listing checkout paths.
INSTALLED_REPORTER_HOME = "/opt/reporter"


def is_backup_dev_mode(env: Mapping[str, str] | None = None) -> bool:
    """True when the dev wrapper enabled dry-run (repository bin/backup only)."""
    environ = os.environ if env is None else env
    return environ.get(BACKUP_DEV_MODE_ENV, "").strip().lower() in BACKUP_DEV_MODE_TRUTHY


def _dry_run_backed_up_summary(
    backup_dir: Path,
    members: list[tuple[Path, str]],
) -> str | None:
    """Summarize what a production archive would contain (dumps + install tree)."""
    dump_arcnames = sorted(
        arcname for _, arcname in members if arcname.startswith(".backup/")
    )
    if not dump_arcnames and backup_dir.is_dir():
        dump_arcnames = [f".backup/{path.name}" for path in sorted(backup_dir.glob("*.dump"))]

    if dump_arcnames:
        summary = ", ".join(dump_arcnames)
        has_install_files = any(
            not arcname.startswith(".backup/") for _, arcname in members
        )
        if has_install_files:
            summary = f"{summary}, and other files from {INSTALLED_REPORTER_HOME}"
        return summary

    if backup_dir.is_dir():
        backup_files = sorted(path.name for path in backup_dir.iterdir() if path.is_file())
        if backup_files:
            return ", ".join(backup_files)
    return None


def dry_run_messages(
    backup_dir: Path,
    members: list[tuple[Path, str]],
) -> list[str]:
    """Lines to print when skipping archive creation in development mode."""
    lines = [
        "Dry-run: Assuming backup command is running in development mode. "
        "Skipping actual backup....",
    ]
    backed_up = _dry_run_backed_up_summary(backup_dir, members)
    if backed_up:
        lines.append(f"Dry-run: Would have backed up {backed_up}")
    return lines


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
