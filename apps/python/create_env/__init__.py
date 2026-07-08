from ._ask_selects import ENV_SOURCE_DEFAULT, ENV_SOURCE_OPTIONS
from lib.env import default_report_out_dir
from lib.env_backup import default_backup_dir
from .backup import (
    BACKUP_DEFAULT_OVERRIDES,
    BACKUP_FIELDS,
    BACKUP_OUTPUT_ORDER,
    ask_standalone_installation,
    collect_backup_values,
)
from .database import (
    AskSelect,
    ConfigContext,
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
    collect_reporter_values,
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

ENV_SOURCE_OUTPUT_ORDER = ["ENV_SOURCE"]

OUTPUT_GROUPS = [
    DATABASE_OUTPUT_ORDER,
    ENV_SOURCE_OUTPUT_ORDER,
    SYNC_OUTPUT_ORDER,
    REPORTER_OUTPUT_ORDER,
    UI_OUTPUT_ORDER,
    PRIVX_OUTPUT_ORDER,
    BACKUP_OUTPUT_ORDER,
]
OUTPUT_ORDER = [key for group in OUTPUT_GROUPS for key in group]
DEFAULT_OVERRIDES = dict(DATABASE_DEFAULT_OVERRIDES)
DEFAULT_OVERRIDES.update(BACKUP_DEFAULT_OVERRIDES)
DEFAULT_OVERRIDES.setdefault("BACKUP_DIR", default_backup_dir())
DEFAULT_OVERRIDES.setdefault("REPORT_OUT_DIR", default_report_out_dir())
DEFAULT_OVERRIDES.update(PRIVX_DEFAULT_OVERRIDES)


def collect_env_values(
    defaults: dict[str, str],
    prompt_fields: PromptFields,
    ask_select: AskSelect,
    skipped: frozenset[str] = frozenset(),
) -> dict[str, str]:
    values: dict[str, str] = {}

    # Phase 1: Collect database values (context not yet fully known)
    initial_context = ConfigContext(
        skipped=skipped,
        is_standalone_install=False,
        is_db_configured=False,
    )
    values.update(collect_database_values(defaults, prompt_fields, ask_select, initial_context))

    # Phase 2: Gather context information
    print("\nConfiguration source: where should the application read its settings from?")
    env_source = ask_select(
        "Use database or .env file for configuration?",
        options=ENV_SOURCE_OPTIONS,
        default_value=ENV_SOURCE_DEFAULT,
    )
    values["ENV_SOURCE"] = env_source

    print("\nStandalone installation:")
    is_standalone = ask_standalone_installation(ask_select)

    context = ConfigContext(
        skipped=skipped,
        is_standalone_install=(is_standalone == "yes"),
        is_db_configured=(env_source == "db"),
    )

    # Phase 3: Each group decides what to ask based on context
    values.update(collect_reporter_values(defaults, prompt_fields, context))
    values.update(collect_sync_values(defaults, prompt_fields, context))
    values.update(collect_ui_values(defaults, prompt_fields, context))
    values.update(collect_privx_values(defaults, prompt_fields, ask_select, context))
    values.update(collect_backup_values(defaults, prompt_fields, ask_select, context))

    if context.is_db_configured:
        print(
            "\nENV_SOURCE set to 'db'. All remaining configuration is stored in the database.\n"
            "Next step: log in as super admin and complete the configuration there."
        )

    return values


__all__ = [
    "ConfigContext",
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
