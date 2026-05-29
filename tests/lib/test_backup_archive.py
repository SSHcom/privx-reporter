"""Tests for pure archive helpers in lib/_backup/backup_archive.py."""

import tarfile
from pathlib import Path

import pytest

from lib._backup.backup_archive import (
    archive_members,
    latest_dump_per_db,
    parse_running_reporter_containers,
    write_archive,
)


@pytest.mark.unit
def test_parse_running_reporter_containers_filters_known() -> None:
    output = "reporter-ui\nsome-other-container\nreporter-data-db\n"
    assert parse_running_reporter_containers(output) == ["reporter-ui", "reporter-data-db"]


@pytest.mark.unit
def test_parse_running_reporter_containers_empty_when_none_up() -> None:
    assert parse_running_reporter_containers("unrelated\n\n") == []


@pytest.mark.unit
def test_latest_dump_per_db_picks_newest_per_label() -> None:
    files = [
        "admin-20260101T000000Z.dump",
        "admin-20260103T000000Z.dump",
        "data-20260102T000000Z.dump",
    ]
    assert latest_dump_per_db(files) == {
        "admin": "admin-20260103T000000Z.dump",
        "data": "data-20260102T000000Z.dump",
    }


@pytest.mark.unit
def test_archive_members_includes_dumps_and_existing_config(tmp_path: Path) -> None:
    reporter_home = tmp_path
    backup_dir = reporter_home / ".backup"
    backup_dir.mkdir()
    (backup_dir / "admin-20260103T000000Z.dump").write_text("dump")
    (reporter_home / ".env").write_text("BACKUP_CONFIG=true,all,720,5")
    (reporter_home / "docker-compose.yml").write_text("services: {}")
    (reporter_home / ".pg-ssl").mkdir()
    (reporter_home / ".pg-ssl" / "pg_hba.conf").write_text("local all all trust")
    # Note: certs/ deliberately absent -> must be skipped without error.

    members = archive_members(
        reporter_home,
        backup_dir,
        {"admin": "admin-20260103T000000Z.dump"},
    )
    arcnames = sorted(arcname for _, arcname in members)
    assert arcnames == [".backup/admin-20260103T000000Z.dump", ".env", ".pg-ssl", "docker-compose.yml"]


@pytest.mark.unit
def test_write_archive_creates_readable_tar(tmp_path: Path) -> None:
    src = tmp_path / "payload.txt"
    src.write_text("hello")
    dest = tmp_path / "out.tar.gz"

    write_archive(dest, [(src, "payload.txt")])

    with tarfile.open(dest, "r:gz") as tar:
        assert tar.getnames() == ["payload.txt"]
