"""Tests for pure dump helpers in backup_server/dump.py."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from backup_server.dump import (
    DatabaseTarget,
    build_pg_dump_command,
    databases_for_target,
    dump_filename,
    pgsslmode_for,
    snapshots_to_prune,
)

ENV = {
    "DB_ADMIN_HOST": "reporter-admin-db",
    "DB_ADMIN_PORT": "5432",
    "DB_ADMIN_NAME": "report_admin",
    "DB_ADMIN_USER": "postgres",
    "DB_ADMIN_PASSWORD": "adminpw",
    "DB_ADMIN_SSL_MODE": "on",
    "DB_DATA_HOST": "reporter-data-db",
    "DB_DATA_PORT": "5432",
    "DB_DATA_NAME": "report_data",
    "DB_DATA_USER": "postgres",
    "DB_DATA_PASSWORD": "datapw",
    "DB_DATA_SSL_MODE": "off",
}


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ssl_mode", "expected"),
    [("on", "require"), ("ON", "require"), ("off", "disable"), ("", "disable")],
)
def test_pgsslmode_for(ssl_mode: str, expected: str) -> None:
    assert pgsslmode_for(ssl_mode) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("target", "labels"),
    [("admin", ["admin"]), ("data", ["data"]), ("all", ["admin", "data"])],
)
def test_databases_for_target_selects_labels(target: str, labels: list[str]) -> None:
    result = databases_for_target(target, ENV)
    assert [t.label for t in result] == labels


@pytest.mark.unit
def test_databases_for_target_maps_env_fields() -> None:
    (admin,) = databases_for_target("admin", ENV)
    assert admin == DatabaseTarget(
        label="admin",
        host="reporter-admin-db",
        port="5432",
        name="report_admin",
        user="postgres",
        password="adminpw",
        sslmode="require",
    )


@pytest.mark.unit
def test_dump_filename_is_utc_sortable() -> None:
    now = datetime(2026, 5, 26, 7, 8, 9, tzinfo=UTC)
    assert dump_filename("admin", now) == "admin-20260526T070809Z.dump"


@pytest.mark.unit
def test_build_pg_dump_command_uses_custom_format() -> None:
    (data,) = databases_for_target("data", ENV)
    cmd = build_pg_dump_command(data, Path("/opt/reporter/.backup/data-x.dump"))
    assert cmd == [
        "pg_dump",
        "-h", "reporter-data-db",
        "-p", "5432",
        "-U", "postgres",
        "-d", "report_data",
        "-Fc",
        "-f", "/opt/reporter/.backup/data-x.dump",
    ]


@pytest.mark.unit
def test_snapshots_to_prune_keeps_newest_n() -> None:
    files = [
        "admin-20260101T000000Z.dump",
        "admin-20260102T000000Z.dump",
        "admin-20260103T000000Z.dump",
    ]
    assert snapshots_to_prune(files, snapshots=2) == ["admin-20260101T000000Z.dump"]


@pytest.mark.unit
def test_snapshots_to_prune_noop_when_within_limit() -> None:
    files = ["admin-20260101T000000Z.dump"]
    assert snapshots_to_prune(files, snapshots=5) == []
