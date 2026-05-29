"""Tests for lib/env_backup.py runtime configuration parser."""

from unittest.mock import patch

import pytest

from lib.env_backup import (
    DEFAULT_BACKUP_CONFIG,
    BackupConfig,
    parse_backup_config,
)


@pytest.mark.unit
def test_parses_default_config() -> None:
    config = parse_backup_config(DEFAULT_BACKUP_CONFIG)
    assert config == BackupConfig(enabled=True, target="all", interval_minutes=720, snapshots=5)


@pytest.mark.unit
def test_strips_whitespace_and_reads_disabled() -> None:
    config = parse_backup_config("  false , admin , 60 , 1 ")
    assert config == BackupConfig(enabled=False, target="admin", interval_minutes=60, snapshots=1)


@pytest.mark.unit
@patch.dict("os.environ", {"BACKUP_CONFIG": "true,data,1440,3"}, clear=True)
def test_reads_from_environment_when_no_argument() -> None:
    config = parse_backup_config()
    assert config.target == "data"
    assert config.interval_minutes == 1440
    assert config.snapshots == 3


@pytest.mark.unit
@patch.dict("os.environ", {}, clear=True)
def test_falls_back_to_default_when_env_missing() -> None:
    assert parse_backup_config() == BackupConfig(True, "all", 720, 5)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "error_match"),
    [
        ("true,all,720", "must be '<enabled>,<target>,<interval-minutes>,<snapshots>'"),
        ("true,all,720,5,9", "must be '<enabled>,<target>,<interval-minutes>,<snapshots>'"),
        ("maybe,all,720,5", "enabled must be 'true' or 'false'"),
        ("true,everything,720,5", "target must be one of 'admin', 'data', 'all'"),
        ("true,all,x,5", "interval-minutes must be numeric"),
        ("true,all,59,5", "interval-minutes must be at least 60"),
        ("true,all,720,x", "snapshots must be numeric"),
        ("true,all,720,0", "snapshots must be at least 1"),
    ],
)
def test_rejects_invalid_values(raw: str, error_match: str) -> None:
    with pytest.raises(ValueError, match=error_match):
        parse_backup_config(raw)
