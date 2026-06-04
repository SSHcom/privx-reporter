from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import Protocol

from .ask_selects import DB_TOPOLOGY_DEFAULT, DB_TOPOLOGY_OPTIONS

Validator = Callable[[str], tuple[bool, str | None]]


class PromptFields(Protocol):
    def __call__(self, fields: list[FieldDef], defaults: dict[str, str]) -> dict[str, str]: ...


class AskSelect(Protocol):
    def __call__(
        self,
        prompt: str,
        *,
        options: list[tuple[str, str]],
        default_value: str,
    ) -> str: ...


@dataclass(frozen=True)
class FieldDef:
    key: str
    label: str
    description: str
    validator: Validator


def validate_non_empty(value: str) -> tuple[bool, str | None]:
    if value.strip():
        return True, None
    return False, "This value cannot be empty."


def validate_port(value: str) -> tuple[bool, str | None]:
    if not value.isdigit():
        return False, "Port must be numeric."
    port = int(value)
    if 1 <= port <= 65535:
        return True, None
    return False, "Port must be in range 1..65535."


def validate_ssl_mode(value: str) -> tuple[bool, str | None]:
    if value.lower() in {"on", "off"}:
        return True, None
    return False, "SSL mode must be either 'on' or 'off'."


DB_DATA_FIELDS = [
    FieldDef(
        key="DB_DATA_HOST",
        label="Data DB host",
        description="Hostname for the data database connection.",
        validator=validate_non_empty,
    ),
    FieldDef(
        key="DB_DATA_PORT",
        label="Data DB port",
        description="TCP port for the data database connection.",
        validator=validate_port,
    ),
    FieldDef(
        key="DB_DATA_USER",
        label="Data DB user",
        description="Username used to authenticate to the data database.",
        validator=validate_non_empty,
    ),
    FieldDef(
        key="DB_DATA_PASSWORD",
        label="Data DB password",
        description="Password used to authenticate to the data database.",
        validator=validate_non_empty,
    ),
    FieldDef(
        key="DB_DATA_NAME",
        label="Data DB name",
        description="Database name for historical synced records.",
        validator=validate_non_empty,
    ),
    FieldDef(
        key="DB_DATA_SSL_MODE",
        label="Data DB SSL mode (on/off)",
        description="Use 'on' to require SSL, or 'off' to allow plain local connections.",
        validator=validate_ssl_mode,
    ),
]

DB_ADMIN_FIELDS = [
    FieldDef(
        key="DB_ADMIN_HOST",
        label="Admin DB host",
        description="Hostname for the admin/configuration database connection.",
        validator=validate_non_empty,
    ),
    FieldDef(
        key="DB_ADMIN_PORT",
        label="Admin DB port",
        description="TCP port for the admin/configuration database connection.",
        validator=validate_port,
    ),
    FieldDef(
        key="DB_ADMIN_USER",
        label="Admin DB user",
        description="Username used to authenticate to the admin/configuration database.",
        validator=validate_non_empty,
    ),
    FieldDef(
        key="DB_ADMIN_PASSWORD",
        label="Admin DB password",
        description="Password used to authenticate to the admin/configuration database.",
        validator=validate_non_empty,
    ),
    FieldDef(
        key="DB_ADMIN_NAME",
        label="Admin DB name",
        description="Database name for app configuration and session data.",
        validator=validate_non_empty,
    ),
    FieldDef(
        key="DB_ADMIN_SSL_MODE",
        label="Admin DB SSL mode (on/off)",
        description="Use 'on' to require SSL, or 'off' to allow plain local connections.",
        validator=validate_ssl_mode,
    ),
]

ADMIN_FROM_DATA_MAPPING = {
    "DB_ADMIN_HOST": "DB_DATA_HOST",
    "DB_ADMIN_PORT": "DB_DATA_PORT",
    "DB_ADMIN_USER": "DB_DATA_USER",
    "DB_ADMIN_PASSWORD": "DB_DATA_PASSWORD",
    "DB_ADMIN_NAME": "DB_DATA_NAME",
    "DB_ADMIN_SSL_MODE": "DB_DATA_SSL_MODE",
}

DATABASE_OUTPUT_ORDER = [
    "DB_DATA_HOST",
    "DB_DATA_PORT",
    "DB_DATA_USER",
    "DB_DATA_PASSWORD",
    "DB_DATA_NAME",
    "DB_DATA_SSL_MODE",
    "DB_ADMIN_HOST",
    "DB_ADMIN_PORT",
    "DB_ADMIN_USER",
    "DB_ADMIN_PASSWORD",
    "DB_ADMIN_NAME",
    "DB_ADMIN_SSL_MODE",
]

DATABASE_DEFAULT_OVERRIDES = {
    "DB_DATA_PORT": "5432",
    "DB_ADMIN_PORT": "5432",
}


def merge_admin_from_data(values: dict[str, str]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for admin_key, data_key in ADMIN_FROM_DATA_MAPPING.items():
        merged[admin_key] = values[data_key]
    merged["DB_ADMIN_NAME"] = "report_db"
    return merged


def collect_database_values(
    defaults: dict[str, str],
    prompt_fields: PromptFields,
    ask_select: AskSelect,
    *,
    mode: str = "ask",
) -> dict[str, str]:
    if mode == "skip":
        print("\nSkipping database settings.")
        return {}

    if mode == "defaults":
        print("\nUsing provided defaults from .env-example for database settings.")
        values: dict[str, str] = {}
        for field in [*DB_DATA_FIELDS, *DB_ADMIN_FIELDS]:
            value = defaults.get(field.key, "").strip()
            is_valid, message = field.validator(value)
            if not is_valid:
                raise ValueError(f"Missing or invalid default value for {field.key}: {message}")
            values[field.key] = value
        return values

    print("\nDB topology: choose whether data/admin DB use one shared instance or separate instances.")
    topology = ask_select(
        "How should DB instances be configured?",
        options=DB_TOPOLOGY_OPTIONS,
        default_value=DB_TOPOLOGY_DEFAULT,
    )

    if topology == "same_instance":
        data_defaults = dict(defaults)
        data_defaults["DB_DATA_NAME"] = "report_db"
        print("\nConfigure data DB values:")
        values = prompt_fields(DB_DATA_FIELDS, data_defaults)
        values.update(merge_admin_from_data(values))
    else:
        print("\nConfigure data DB values:")
        values = prompt_fields(DB_DATA_FIELDS, defaults)
        print("\nConfigure admin DB values:")
        values.update(prompt_fields(DB_ADMIN_FIELDS, defaults))

    return values
