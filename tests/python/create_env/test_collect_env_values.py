from __future__ import annotations

from typing import TYPE_CHECKING

from create_env import collect_env_values

if TYPE_CHECKING:
    import pytest

    from create_env.database import FieldDef


def test_non_standalone_env_mode_omits_sync_ui_and_backup(
    capsys: pytest.CaptureFixture[str],
) -> None:
    prompted_keys: list[str] = []
    ask_prompts: list[str] = []

    def prompt_fields(fields: list[FieldDef], defaults: dict[str, str]) -> dict[str, str]:
        prompted_keys.extend(field.key for field in fields)
        return {field.key: defaults.get(field.key, f"value-for-{field.key}") for field in fields}

    def ask_select(
        prompt: str,
        options: list[tuple[str, str]],
        default_value: str,
    ) -> str:
        ask_prompts.append(prompt)
        if "DB instances" in prompt:
            return "same_instance"
        if "database or .env file" in prompt:
            return "env"
        if "standalone installation" in prompt:
            return "no"
        if "PRIVX_CA_CERT" in prompt:
            return "skip"
        raise AssertionError(f"unexpected ask_select prompt: {prompt}")

    values = collect_env_values(
        {
            "DB_DATA_HOST": "localhost",
            "DB_DATA_PORT": "5444",
            "DB_DATA_USER": "postgres",
            "DB_DATA_PASSWORD": "postgres",
            "DB_DATA_NAME": "report_data",
            "DB_DATA_SSL_MODE": "on",
            "DB_ADMIN_HOST": "localhost",
            "DB_ADMIN_PORT": "5445",
            "DB_ADMIN_USER": "postgres",
            "DB_ADMIN_PASSWORD": "postgres",
            "DB_ADMIN_NAME": "report_admin",
            "DB_ADMIN_SSL_MODE": "on",
            "REPORT_OUT_DIR": "/home/testuser/REPORTS",
            "REPORT_API_BATCH_SIZE": "500",
            "PRIVX_HOSTNAME": "privx.example.com",
            "PRIVX_PORT": "443",
            "PRIVX_API_OAUTH_CLIENT_ID": "privx-external",
            "PRIVX_API_OAUTH_CLIENT_SECRET": "secret",
            "PRIVX_API_CLIENT_ID": "api-client",
            "PRIVX_API_CLIENT_SECRET": "api-secret",
            "PRIVX_CA_CERT": "",
        },
        prompt_fields,
        ask_select,
    )

    assert "SYNC_BATCH_SIZE" not in values
    assert "UI_JWT_EXPIRATION_MINUTES" not in values
    assert "BACKUP_DIR" not in values
    assert values["REPORT_API_BATCH_SIZE"] == "500"
    assert values["PRIVX_HOSTNAME"] == "privx.example.com"
    output = capsys.readouterr().out
    assert "Skipping sync settings (not a standalone installation)" in output
    assert "Skipping UI settings (not a standalone installation)" in output
    assert "Skipping backup configuration (not a standalone installation)" in output
    assert not any(key.startswith("SYNC_") for key in prompted_keys)
    assert not any(key.startswith("UI_") for key in prompted_keys)
