"""Tests for lib/env_sync.py configuration module."""

import logging
from unittest.mock import patch

import pytest

from lib.env_sync import (
    AUDIT_EVENT_SOURCE,
    CONNECTION_SOURCE,
    DEFAULT_SYNC_CONFIG,
    DEFAULT_SYNC_MAX_RECORDS_PER_WINDOW,
    DEFAULT_SYNC_WINDOW_SIZE_DOWN_MINUTES,
    DEFAULT_SYNC_WINDOW_SIZES_MINUTES,
    SYNC_AUDIT,
    SYNC_BATCH_SIZE,
    SYNC_CONNECTION,
    SYNC_MAX_RANGE_HOURS,
    SYNC_MAX_RECORDS_PER_WINDOW,
    SYNC_SOURCES,
    SYNC_TREND_HOUR,
    SYNC_WINDOW_SIZE_DOWN_MINUTES,
    SYNC_WINDOW_SIZES_MINUTES,
    SyncConfig,
    SyncConfigValues,
    parse_retention_days,
)


@pytest.mark.unit
@patch.dict(
    "os.environ",
    {
        SYNC_SOURCES: f"  {AUDIT_EVENT_SOURCE} , {CONNECTION_SOURCE} ",
        SYNC_AUDIT: "60,15,30",
        SYNC_CONNECTION: "30,10,7",
        SYNC_BATCH_SIZE: "100",
    },
    clear=True,
)
def test_init_parses_sources_and_configs() -> None:
    config = SyncConfig()

    assert config.sources == [AUDIT_EVENT_SOURCE, CONNECTION_SOURCE]
    assert config.batch_size == 100
    assert config.max_range_hours == 2191
    assert config.window_sizes_minutes == DEFAULT_SYNC_WINDOW_SIZES_MINUTES
    assert config.max_records_per_window == DEFAULT_SYNC_MAX_RECORDS_PER_WINDOW
    assert config.window_size_down_minutes == DEFAULT_SYNC_WINDOW_SIZE_DOWN_MINUTES
    assert config.sync_trend_hour is None
    assert config.audit_event_config is not None
    assert config.connection_config is not None

    values = config.get_config_values()
    assert isinstance(values, SyncConfigValues)


@pytest.mark.unit
@patch.dict("os.environ", {SYNC_SOURCES: AUDIT_EVENT_SOURCE}, clear=True)
def test_init_uses_default_sync_config() -> None:
    config = SyncConfig()
    default_parts = DEFAULT_SYNC_CONFIG.split(",")
    assert config.audit_event_config is not None
    assert config.audit_event_config.minutes == int(default_parts[0])
    assert config.audit_event_config.range_minutes == int(default_parts[1])
    assert config.audit_event_config.retention_days == int(default_parts[2])
    assert config.window_sizes_minutes == DEFAULT_SYNC_WINDOW_SIZES_MINUTES
    assert config.max_records_per_window == DEFAULT_SYNC_MAX_RECORDS_PER_WINDOW
    assert config.window_size_down_minutes == DEFAULT_SYNC_WINDOW_SIZE_DOWN_MINUTES


@pytest.mark.unit
@patch.dict(
    "os.environ",
    {
        SYNC_SOURCES: AUDIT_EVENT_SOURCE,
        SYNC_AUDIT: "60,15,30",
        SYNC_WINDOW_SIZES_MINUTES: "5,10,15",
        SYNC_MAX_RECORDS_PER_WINDOW: "40000",
        SYNC_WINDOW_SIZE_DOWN_MINUTES: "5",
    },
    clear=True,
)
def test_init_parses_window_configuration() -> None:
    config = SyncConfig()
    assert config.window_sizes_minutes == [5, 10, 15]
    assert config.max_records_per_window == 40_000
    assert config.window_size_down_minutes == 5


@pytest.mark.unit
@patch.dict(
    "os.environ",
    {
        SYNC_SOURCES: AUDIT_EVENT_SOURCE,
        SYNC_AUDIT: "60,15,30",
        SYNC_TREND_HOUR: "1",
    },
    clear=True,
)
def test_init_parses_sync_trend_hour() -> None:
    config = SyncConfig()
    assert config.sync_trend_hour == 1


@pytest.mark.unit
@pytest.mark.parametrize(
    ("env_patch", "error_match"),
    [
        ({}, f"{SYNC_SOURCES} must be a comma-separated list"),
        ({SYNC_SOURCES: AUDIT_EVENT_SOURCE, SYNC_BATCH_SIZE: "0", SYNC_AUDIT: "60,15,30"}, f"{SYNC_BATCH_SIZE}"),
        ({SYNC_SOURCES: AUDIT_EVENT_SOURCE, SYNC_AUDIT: "0,15,30"}, "minutes must be > 0"),
        ({SYNC_SOURCES: AUDIT_EVENT_SOURCE, SYNC_AUDIT: "60,0,30"}, "range_minutes must be > 0"),
        ({SYNC_SOURCES: CONNECTION_SOURCE, SYNC_CONNECTION: "60,10,0"}, "retention_days must be > 0"),
        (
            {
                SYNC_SOURCES: AUDIT_EVENT_SOURCE,
                SYNC_AUDIT: "60,10,30",
                SYNC_WINDOW_SIZES_MINUTES: "5,-1,10",
            },
            f"{SYNC_WINDOW_SIZES_MINUTES} must contain only positive integers",
        ),
        (
            {
                SYNC_SOURCES: AUDIT_EVENT_SOURCE,
                SYNC_AUDIT: "60,10,30",
                SYNC_WINDOW_SIZES_MINUTES: "5,foo,10",
            },
            f"{SYNC_WINDOW_SIZES_MINUTES} must contain only integer values",
        ),
        (
            {
                SYNC_SOURCES: AUDIT_EVENT_SOURCE,
                SYNC_AUDIT: "60,10,30",
                SYNC_MAX_RECORDS_PER_WINDOW: "0",
            },
            f"{SYNC_MAX_RECORDS_PER_WINDOW} must be a positive integer",
        ),
        (
            {
                SYNC_SOURCES: AUDIT_EVENT_SOURCE,
                SYNC_AUDIT: "60,10,30",
                SYNC_WINDOW_SIZE_DOWN_MINUTES: "0",
            },
            f"{SYNC_WINDOW_SIZE_DOWN_MINUTES} must be a positive integer",
        ),
        (
            {
                SYNC_SOURCES: AUDIT_EVENT_SOURCE,
                SYNC_AUDIT: "60,10,30",
                SYNC_MAX_RANGE_HOURS: "0",
            },
            f"{SYNC_MAX_RANGE_HOURS} must be a positive integer",
        ),
        (
            {
                SYNC_SOURCES: AUDIT_EVENT_SOURCE,
                SYNC_AUDIT: "60,10,30",
                SYNC_TREND_HOUR: "-1",
            },
            f"{SYNC_TREND_HOUR} must be in range 0..23",
        ),
        (
            {
                SYNC_SOURCES: AUDIT_EVENT_SOURCE,
                SYNC_AUDIT: "60,10,30",
                SYNC_TREND_HOUR: "24",
            },
            f"{SYNC_TREND_HOUR} must be in range 0..23",
        ),
        (
            {
                SYNC_SOURCES: AUDIT_EVENT_SOURCE,
                SYNC_AUDIT: "60,10,30",
                SYNC_TREND_HOUR: "abc",
            },
            f"{SYNC_TREND_HOUR} must be an integer in range 0..23",
        ),
    ],
)
def test_validate_rejects_invalid_values(env_patch: dict[str, str], error_match: str) -> None:
    with patch.dict("os.environ", env_patch, clear=True):
        with pytest.raises(ValueError, match=error_match):
            SyncConfig()


@pytest.mark.unit
@patch.dict(
    "os.environ",
    {
        SYNC_SOURCES: f"{AUDIT_EVENT_SOURCE},{CONNECTION_SOURCE}",
        SYNC_AUDIT: "60,15,30",
        SYNC_CONNECTION: "30,10,7",
    },
    clear=True,
)
def test_log_config_values_emits_core_lines(caplog: pytest.LogCaptureFixture) -> None:
    config = SyncConfig()
    with caplog.at_level(logging.INFO, logger="lib.env_sync"):
        config.log_config_values()

    joined = " ".join(record.message for record in caplog.records)
    assert "Sync sources" in joined
    assert "Audit sync interval" in joined
    assert "Connection sync interval" in joined
    assert "Sync max range" in joined
    assert "Sync trend daily hour (UTC)" in joined


@pytest.mark.unit
@patch.dict("os.environ", {SYNC_AUDIT: "60,15,45"}, clear=True)
def test_parse_retention_days_reads_third_value() -> None:
    assert parse_retention_days(SYNC_AUDIT) == 45


@pytest.mark.unit
@patch.dict("os.environ", {SYNC_AUDIT: "60,15"}, clear=True)
def test_parse_retention_days_rejects_bad_shape() -> None:
    with pytest.raises(ValueError, match="must contain exactly 3"):
        parse_retention_days(SYNC_AUDIT)
