from __future__ import annotations

from lib.env_backup import DEFAULT_BACKUP_CONFIG, default_backup_dir

from .database import AskSelect, ConfigContext, FieldDef, PromptFields, validate_non_empty

BACKUP_ENABLED_VALUES = {"true", "false"}
BACKUP_TARGET_VALUES = {"admin", "data", "all"}
BACKUP_INTERVAL_MINUTES_MIN = 60
BACKUP_SNAPSHOTS_MIN = 1


def validate_backup_config(value: str) -> tuple[bool, str | None]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        return False, "Value must be '<enabled>,<target>,<interval-minutes>,<snapshots>'."

    enabled, target, interval_minutes, snapshots = parts

    if enabled not in BACKUP_ENABLED_VALUES:
        return False, "Enabled must be either 'true' or 'false'."

    if target not in BACKUP_TARGET_VALUES:
        return False, "Target must be one of 'admin', 'data', or 'all'."

    if not interval_minutes.isdigit():
        return False, "Interval minutes must be numeric."
    if int(interval_minutes) < BACKUP_INTERVAL_MINUTES_MIN:
        return False, "Interval minutes must be at least 60."

    if not snapshots.isdigit():
        return False, "Snapshots must be numeric."
    if int(snapshots) < BACKUP_SNAPSHOTS_MIN:
        return False, "Snapshots must be at least 1."

    return True, None


BACKUP_DIR_FIELD = FieldDef(
    key="BACKUP_DIR",
    label="Backup directory path",
    description="Directory where backup_server stores database dump files.",
    validator=validate_non_empty,
)

BACKUP_FIELDS = [
    FieldDef(
        key="BACKUP_CONFIG",
        label="Backup config (<enabled>,<target>,<interval-minutes>,<snapshots>)",
        description=(
            "Backup config in format '<enabled>,<target>,<interval-minutes>,<snapshots>', for example 'true,all,720,5'."
        ),
        validator=validate_backup_config,
    ),
    BACKUP_DIR_FIELD,
]

BACKUP_OUTPUT_ORDER = [
    "BACKUP_CONFIG",
    "BACKUP_DIR",
]

BACKUP_DEFAULT_OVERRIDES = {
    "BACKUP_CONFIG": DEFAULT_BACKUP_CONFIG,
}


def _disabled_backup_config(defaults: dict[str, str]) -> str:
    configured = defaults.get("BACKUP_CONFIG", BACKUP_DEFAULT_OVERRIDES["BACKUP_CONFIG"]).strip()
    is_valid, _ = validate_backup_config(configured)
    if not is_valid:
        configured = BACKUP_DEFAULT_OVERRIDES["BACKUP_CONFIG"]
    _, target, interval_minutes, snapshots = [part.strip() for part in configured.split(",")]
    return f"false,{target},{interval_minutes},{snapshots}"


STANDALONE_OPTIONS = [("yes", "Yes"), ("no", "No")]
STANDALONE_DEFAULT = "yes"


def ask_standalone_installation(ask_select: AskSelect) -> str:
    return ask_select(
        "Are we using a standalone installation (everything on the same host)?",
        options=STANDALONE_OPTIONS,
        default_value=STANDALONE_DEFAULT,
    )


def _ask_enable_backup(ask_select: AskSelect) -> str:
    return ask_select(
        "Should backup of the databases be enabled?",
        options=[("yes", "Yes"), ("no", "No")],
        default_value="yes",
    )


def _resolve_backup_dir(defaults: dict[str, str]) -> str:
    backup_dir = defaults.get("BACKUP_DIR", default_backup_dir()).strip()
    if not backup_dir:
        backup_dir = default_backup_dir()
    return backup_dir


def _print_db_backup_intro() -> None:
    print(
        "\nWhen using the database for configuration, backup defaults to:"
        f"\n  BACKUP_CONFIG={DEFAULT_BACKUP_CONFIG} (disabled, all databases, every 720 minutes, keep 5 snapshots)"
        "\n\nWe do however need to set the backup directory."
        "\nYou can change backup schedule in the Admin UI app config page after login."
    )


def collect_backup_values(
    defaults: dict[str, str],
    prompt_fields: PromptFields,
    ask_select: AskSelect,
    context: ConfigContext,
) -> dict[str, str]:
    if "backup" in context.skipped:
        print("\nSkipping backup configuration (explicitly skipped).")
        return {}

    if not context.is_standalone_install:
        print("\nSkipping backup configuration (not a standalone installation).")
        return {}

    if context.is_db_configured:
        _print_db_backup_intro()
        return prompt_fields([BACKUP_DIR_FIELD], defaults)

    enable_backup = _ask_enable_backup(ask_select)

    if enable_backup != "yes":
        print("\nSkipping backup config prompt and disabling database backups.")
        return {"BACKUP_CONFIG": _disabled_backup_config(defaults), "BACKUP_DIR": _resolve_backup_dir(defaults)}

    print("\nConfigure backup values:")
    print("  - enabled: true|false (default: true)")
    print("  - target: admin|data|all (default: all)")
    print("  - interval-minutes: backup frequency in minutes (default: 720, minimum: 60)")
    print("  - snapshots: how many backup snapshots to rotate/keep (default: 5, minimum: 1)")
    print(f"  - backup directory: where backup_server stores dump files (default: {default_backup_dir()})")
    return prompt_fields(BACKUP_FIELDS, defaults)
