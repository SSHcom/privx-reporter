from __future__ import annotations

from .database import ConfigContext, FieldDef, PromptFields, validate_non_empty


def validate_positive_int(value: str) -> tuple[bool, str | None]:
    if not value.isdigit():
        return False, "Value must be numeric."
    if int(value) > 0:
        return True, None
    return False, "Value must be greater than zero."


def validate_hour_utc(value: str) -> tuple[bool, str | None]:
    if not value.isdigit():
        return False, "Value must be numeric."
    hour = int(value)
    if 0 <= hour <= 23:
        return True, None
    return False, "Value must be in range 0..23."


SYNC_FIELDS = [
    FieldDef(
        key="SYNC_BATCH_SIZE",
        label="Sync API batch size",
        description="Batch size used for PrivX API calls during sync.",
        validator=validate_positive_int,
    ),
    FieldDef(
        key="SYNC_WINDOW_SIZES_MINUTES",
        label="Sync window sizes (comma-separated minutes)",
        description="Allowed adaptive window sizes in minutes, for example 8,12,16,20.",
        validator=validate_non_empty,
    ),
    FieldDef(
        key="SYNC_WINDOW_SIZE_DOWN_MINUTES",
        label="Sync window down step (minutes)",
        description="Decrease step used when sync windows are shrunk.",
        validator=validate_positive_int,
    ),
    FieldDef(
        key="SYNC_MAX_RECORDS_PER_WINDOW",
        label="Sync max records per window",
        description="Record threshold used to grow or shrink adaptive windows.",
        validator=validate_positive_int,
    ),
    FieldDef(
        key="SYNC_MAX_RANGE_HOURS",
        label="Sync max range (hours)",
        description="Maximum catch-up look-back range in hours.",
        validator=validate_positive_int,
    ),
    FieldDef(
        key="SYNC_SOURCES",
        label="Sync sources (comma-separated)",
        description="Source order to sync, for example trends,concurrent,connection,audit.",
        validator=validate_non_empty,
    ),
    FieldDef(
        key="SYNC_TREND_HOUR",
        label="Sync trend refresh hour (UTC, 0..23)",
        description="UTC hour for daily system trend refresh.",
        validator=validate_hour_utc,
    ),
    FieldDef(
        key="SYNC_CONNECTION",
        label="Sync connection config",
        description=("Connection sync config as interval,initial range (on first run),retention."),
        validator=validate_non_empty,
    ),
    FieldDef(
        key="SYNC_AUDIT",
        label="Sync audit config",
        description=("Audit sync config as interval,initial range (on first run),retention."),
        validator=validate_non_empty,
    ),
]

SYNC_OUTPUT_ORDER = [
    "SYNC_BATCH_SIZE",
    "SYNC_WINDOW_SIZES_MINUTES",
    "SYNC_WINDOW_SIZE_DOWN_MINUTES",
    "SYNC_MAX_RECORDS_PER_WINDOW",
    "SYNC_MAX_RANGE_HOURS",
    "SYNC_SOURCES",
    "SYNC_TREND_HOUR",
    "SYNC_CONNECTION",
    "SYNC_AUDIT",
]


def collect_sync_values(
    defaults: dict[str, str],
    prompt_fields: PromptFields,
    context: ConfigContext,
) -> dict[str, str]:
    if not context.is_standalone_install:
        print("\nSkipping sync settings (not a standalone installation).")
        return {}

    if context.is_db_configured:
        print("\nSkipping sync settings (configuration stored in database).")
        return {}

    if "sync" in context.skipped:
        print("\nSkipping sync settings (using default values).")
        return {key: defaults[key] for key in SYNC_OUTPUT_ORDER if key in defaults}

    print("\nConfigure sync values:")
    return prompt_fields(SYNC_FIELDS, defaults)
