"""Tests for lib/_backup/backup.py archive CLI."""

from __future__ import annotations

import sys
import tarfile
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from lib._backup import backup as backup_cli
from lib._backup.backup_archive import BACKUP_DEV_MODE_ENV


def _install_tree(reporter_home: Path) -> Path:
    """Minimal reporter home layout for archive creation."""
    backup_dir = reporter_home / ".backup"
    backup_dir.mkdir()
    (backup_dir / "admin-20260101T000000Z.dump").write_text("old-admin")
    (backup_dir / "admin-20260103T000000Z.dump").write_text("new-admin")
    (backup_dir / "data-20260102T000000Z.dump").write_text("data")
    (reporter_home / ".env").write_text("BACKUP_CONFIG=true,all,720,5\n")
    (reporter_home / "docker-compose.yml").write_text("services: {}\n")
    return backup_dir


def _tar_members(archive: Path) -> list[str]:
    with tarfile.open(archive, "r:gz") as tar:
        return sorted(tar.getnames())


@pytest.mark.unit
def test_main_writes_archive_with_latest_dumps_and_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reporter_home = tmp_path / "reporter"
    reporter_home.mkdir()
    _install_tree(reporter_home)
    destination = tmp_path / "archives"
    monkeypatch.delenv(BACKUP_DEV_MODE_ENV, raising=False)
    monkeypatch.setattr(backup_cli, "running_reporter_containers", lambda: [])
    fixed_now = datetime(2026, 6, 3, 12, 0, 0, tzinfo=UTC)
    monkeypatch.setattr(backup_cli, "datetime", MagicMock(now=lambda tz=None: fixed_now))
    monkeypatch.setattr(
        sys,
        "argv",
        ["backup", str(destination), "--reporter-home", str(reporter_home)],
    )

    assert backup_cli.main() == 0

    archive = destination / "reporter-backup-20260603T120000Z.tar.gz"
    assert archive.is_file()
    assert _tar_members(archive) == [
        ".backup/admin-20260103T000000Z.dump",
        ".backup/data-20260102T000000Z.dump",
        ".env",
        "docker-compose.yml",
    ]
    with tarfile.open(archive, "r:gz") as tar:
        admin = tar.extractfile(".backup/admin-20260103T000000Z.dump")
        assert admin is not None
        assert admin.read() == b"new-admin"


@pytest.mark.unit
def test_main_dev_mode_dry_run_skips_archive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    reporter_home = tmp_path / "reporter"
    reporter_home.mkdir()
    _install_tree(reporter_home)
    destination = tmp_path / "archives"
    monkeypatch.setenv(BACKUP_DEV_MODE_ENV, "1")
    monkeypatch.setattr(
        sys,
        "argv",
        ["backup", str(destination), "--reporter-home", str(reporter_home)],
    )

    assert backup_cli.main() == 0

    assert not destination.exists()
    out = capsys.readouterr().out
    assert "Dry-run: Assuming backup command is running in development mode" in out
    assert ".backup/admin-20260103T000000Z.dump" in out
    assert "and other files from /opt/reporter" in out


@pytest.mark.unit
def test_main_fails_when_reporter_containers_running(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    reporter_home = tmp_path / "reporter"
    reporter_home.mkdir()
    _install_tree(reporter_home)
    monkeypatch.delenv(BACKUP_DEV_MODE_ENV, raising=False)
    monkeypatch.setattr(
        backup_cli,
        "running_reporter_containers",
        lambda: ["reporter-ui", "reporter-data-db"],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["backup", str(tmp_path / "out"), "--reporter-home", str(reporter_home)],
    )

    assert backup_cli.main() == 1
    assert "reporter-ui" in capsys.readouterr().err


@pytest.mark.unit
def test_main_fails_when_no_dumps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    reporter_home = tmp_path / "reporter"
    reporter_home.mkdir()
    backup_dir = reporter_home / ".backup"
    backup_dir.mkdir()
    monkeypatch.delenv(BACKUP_DEV_MODE_ENV, raising=False)
    monkeypatch.setattr(backup_cli, "running_reporter_containers", lambda: [])
    monkeypatch.setattr(
        sys,
        "argv",
        ["backup", str(tmp_path / "out"), "--reporter-home", str(reporter_home)],
    )

    assert backup_cli.main() == 1
    assert "no database dumps" in capsys.readouterr().err
