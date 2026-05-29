from __future__ import annotations

from .database import FieldDef, PromptFields, validate_non_empty


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
        key="UI_TMP_ADMIN_PASSWORD",
        label="UI temporary admin password",
        description="Bootstrap admin password for first login on a fresh admin database.",
        validator=validate_non_empty,
    ),
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
]

UI_OUTPUT_ORDER = [
    "UI_TMP_ADMIN_PASSWORD",
    "UI_JWT_EXPIRATION_MINUTES",
    "UI_COOKIE_MAX_AGE_MINUTES",
    "UI_ENABLE_SESSION_DEBUG",
    "UI_AUTH_MODE",
]


def collect_ui_values(
    defaults: dict[str, str],
    prompt_fields: PromptFields,
    *,
    mode: str = "ask",
) -> dict[str, str]:
    if mode == "skip":
        print("\nSkipping UI settings.")
        return {}

    if mode == "defaults":
        print("\nUsing provided defaults from .env-example for UI settings.")
        values: dict[str, str] = {}
        tmp_password_field = next(field for field in UI_FIELDS if field.key == "UI_TMP_ADMIN_PASSWORD")
        for field in UI_FIELDS:
            if field.key == "UI_TMP_ADMIN_PASSWORD":
                continue
            value = defaults.get(field.key, "").strip()
            is_valid, message = field.validator(value)
            if not is_valid:
                raise ValueError(f"Missing or invalid default value for {field.key}: {message}")
            values[field.key] = value

        # Always ask for a temporary admin password, even in defaults mode.
        password_defaults = dict(defaults)
        password_defaults["UI_TMP_ADMIN_PASSWORD"] = ""
        values.update(prompt_fields([tmp_password_field], password_defaults))
        values["UI_AUTH_MODE"] = defaults.get("UI_AUTH_MODE", "local")
        print(
            "\nNOTE: UI_AUTH_MODE is kept as default (local). For OIDC setup details, see "
            "docs/architecture/oidc/OIDC_UI_AUTH.md."
        )
        return values

    print("\nConfigure UI values:")
    ui_defaults = dict(defaults)
    ui_defaults["UI_TMP_ADMIN_PASSWORD"] = ""
    values = prompt_fields(UI_FIELDS, ui_defaults)
    values["UI_AUTH_MODE"] = defaults.get("UI_AUTH_MODE", "local")
    print(
        "\nNOTE: UI_AUTH_MODE is kept as default (local). For OIDC setup details, see "
        "docs/architecture/oidc/OIDC_UI_AUTH.md."
    )
    return values
