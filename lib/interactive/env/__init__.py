from .backup import (
    BACKUP_DEFAULT_OVERRIDES,
    BACKUP_FIELDS,
    BACKUP_OUTPUT_ORDER,
    collect_backup_values,
)
from .database import (
    AskSelect,
    DB_ADMIN_FIELDS,
    DB_DATA_FIELDS,
    DATABASE_DEFAULT_OVERRIDES,
    DATABASE_OUTPUT_ORDER,
    FieldDef,
    PromptFields,
    collect_database_values,
    validate_non_empty,
)
from .privx import (
    PRIVX_FIELDS,
    PRIVX_DEFAULT_OVERRIDES,
    PRIVX_OPTIONAL_FIELDS,
    PRIVX_OUTPUT_ORDER,
    collect_privx_values,
)
from .reporter import (
    REPORT_FIELDS,
    REPORTER_OUTPUT_ORDER,
)
from .sync import (
    SYNC_FIELDS,
    SYNC_OUTPUT_ORDER,
    collect_sync_values,
)
from .ui import (
    UI_FIELDS,
    UI_OUTPUT_ORDER,
    collect_ui_values,
)

OUTPUT_GROUPS = [
    DATABASE_OUTPUT_ORDER,
    SYNC_OUTPUT_ORDER,
    REPORTER_OUTPUT_ORDER,
    UI_OUTPUT_ORDER,
    PRIVX_OUTPUT_ORDER,
    BACKUP_OUTPUT_ORDER,
]
OUTPUT_ORDER = [key for group in OUTPUT_GROUPS for key in group]
DEFAULT_OVERRIDES = dict(DATABASE_DEFAULT_OVERRIDES)
DEFAULT_OVERRIDES.update(BACKUP_DEFAULT_OVERRIDES)
DEFAULT_OVERRIDES.update(PRIVX_DEFAULT_OVERRIDES)


def collect_env_values(
    defaults: dict[str, str],
    prompt_fields: PromptFields,
    ask_select: AskSelect,
    *,
    db_mode: str = "ask",
    sync_mode: str = "ask",
    ui_mode: str = "ask",
) -> dict[str, str]:
    values = collect_database_values(defaults, prompt_fields, ask_select, mode=db_mode)
    values.update(collect_sync_values(defaults, prompt_fields, mode=sync_mode))
    print("\nConfigure report values:")
    values.update(prompt_fields(REPORT_FIELDS, defaults))
    values.update(collect_ui_values(defaults, prompt_fields, mode=ui_mode))
    values.update(collect_privx_values(defaults, prompt_fields, ask_select))
    print("\nConfigure values for 'standalone' installation:")
    values.update(collect_backup_values(defaults, prompt_fields, ask_select))
    return values


__all__ = [
    "DB_ADMIN_FIELDS",
    "DB_DATA_FIELDS",
    "DEFAULT_OVERRIDES",
    "BACKUP_FIELDS",
    "FieldDef",
    "OUTPUT_GROUPS",
    "OUTPUT_ORDER",
    "PRIVX_FIELDS",
    "PRIVX_OPTIONAL_FIELDS",
    "REPORT_FIELDS",
    "SYNC_FIELDS",
    "UI_FIELDS",
    "collect_env_values",
    "validate_non_empty",
]
