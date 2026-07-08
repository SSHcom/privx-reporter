from __future__ import annotations

from .database import ConfigContext, FieldDef, PromptFields


def validate_positive_int(value: str) -> tuple[bool, str | None]:
    if not value.isdigit():
        return False, "Value must be numeric."
    if int(value) > 0:
        return True, None
    return False, "Value must be greater than zero."


def validate_bool_text(value: str) -> tuple[bool, str | None]:
    if value.lower() in {"true", "false"}:
        return True, None
    return False, "Value must be either 'true' or 'false'."


UI_FIELDS = [
    FieldDef(
        key="UI_JWT_EXPIRATION_MINUTES",
        label="UI JWT expiration (minutes)",
        description="Idle session expiration timeout in minutes.",
        validator=validate_positive_int,
    ),
    FieldDef(
        key="UI_COOKIE_MAX_AGE_MINUTES",
        label="UI cookie max age (minutes)",
        description="Browser cookie max age in minutes.",
        validator=validate_positive_int,
    ),
    FieldDef(
        key="UI_ENABLE_SESSION_DEBUG",
        label="Enable UI session debug (true/false)",
        description="Set true to enable session debug panel in own profile view.",
        validator=validate_bool_text,
    ),
    FieldDef(
        key="UI_COLLAPSE_LOCAL_LOGIN",
        label="Collapse local login (true/false)",
        description="Show local login in a collapsible section below OIDC buttons.",
        validator=validate_bool_text,
    ),
]

UI_OUTPUT_ORDER = [
    "UI_JWT_EXPIRATION_MINUTES",
    "UI_COOKIE_MAX_AGE_MINUTES",
    "UI_ENABLE_SESSION_DEBUG",
    "UI_COLLAPSE_LOCAL_LOGIN",
    "OIDC_1_ENABLED",
    "OIDC_2_ENABLED",
]


def collect_ui_values(
    defaults: dict[str, str],
    prompt_fields: PromptFields,
    context: ConfigContext,
) -> dict[str, str]:
    if not context.is_standalone_install:
        print("\nSkipping UI settings (not a standalone installation).")
        return {}

    if context.is_db_configured:
        print("\nSkipping UI settings (configuration stored in database).")
        return {}

    if "ui" in context.skipped:
        print("\nSkipping UI settings (using default values).")
        return {key: defaults[key] for key in UI_OUTPUT_ORDER if key in defaults}

    print("\nConfigure UI values:")
    values = prompt_fields(UI_FIELDS, defaults)
    values["OIDC_1_ENABLED"] = defaults.get("OIDC_1_ENABLED", "false")
    values["OIDC_2_ENABLED"] = defaults.get("OIDC_2_ENABLED", "false")
    print(
        "\nNOTE: OIDC providers are disabled by default. For OIDC setup details, see "
        "docs/operations/OIDC_UI_AUTH_GUIDE.md."
    )
    return values
