from __future__ import annotations

from typing import TYPE_CHECKING, Never

from create_env.backup import collect_backup_values
from create_env.database import ConfigContext

if TYPE_CHECKING:
    import pytest

    from create_env.database import FieldDef
from lib.env_backup import DEFAULT_BACKUP_CONFIG, default_backup_dir


def _context(
    *,
    skipped: frozenset[str] = frozenset(),
    is_standalone_install: bool = True,
    is_db_configured: bool = False,
) -> ConfigContext:
    return ConfigContext(
        skipped=skipped,
        is_standalone_install=is_standalone_install,
        is_db_configured=is_db_configured,
    )


def test_collect_backup_values_prompts_for_backup_dir_only_when_db_configured(
    capsys: pytest.CaptureFixture[str],
) -> None:
    prompted_fields: list[str] = []

    def prompt_fields(fields: list[FieldDef], defaults: dict[str, str]) -> dict[str, str]:
        prompted_fields.extend(field.key for field in fields)
        return {"BACKUP_DIR": "/data/backups"}

    def ask_select(
        prompt: str,
        options: list[tuple[str, str]],
        default_value: str,
    ) -> Never:
        raise AssertionError("should not prompt when db configured")

    context = _context(is_standalone_install=True, is_db_configured=True)
    values = collect_backup_values({}, prompt_fields, ask_select, context)

    assert values == {"BACKUP_DIR": "/data/backups"}
    assert prompted_fields == ["BACKUP_DIR"]
    output = capsys.readouterr().out
    assert DEFAULT_BACKUP_CONFIG in output
    assert "backup defaults to" in output
    assert "disabled, all databases" in output
    assert "need to set the backup directory" in output
    assert "Admin UI app config page" in output


def test_collect_backup_values_skips_when_not_standalone(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def ask_select(
        prompt: str,
        options: list[tuple[str, str]],
        default_value: str,
    ) -> Never:
        raise AssertionError("backup prompts should not run for non-standalone installs")

    context = _context(is_standalone_install=False, is_db_configured=False)
    values = collect_backup_values({}, lambda fields, defaults: {}, ask_select, context)

    assert values == {}
    assert "Skipping backup configuration" in capsys.readouterr().out


def test_collect_backup_values_skips_when_explicitly_skipped(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def ask_select(
        prompt: str,
        options: list[tuple[str, str]],
        default_value: str,
    ) -> Never:
        raise AssertionError("backup prompts should not run when skipped")

    context = _context(skipped=frozenset({"backup"}), is_standalone_install=True)
    values = collect_backup_values({}, lambda fields, defaults: {}, ask_select, context)

    assert values == {}
    assert "explicitly skipped" in capsys.readouterr().out


def test_collect_backup_values_asks_enable_backup() -> None:
    ask_calls: list[str] = []

    def ask_select(
        prompt: str,
        options: list[tuple[str, str]],
        default_value: str,
    ) -> str:
        ask_calls.append(prompt)
        return "yes"

    def prompt_fields(fields: list[FieldDef], defaults: dict[str, str]) -> dict[str, str]:
        return {
            "BACKUP_CONFIG": "true,all,720,5",
            "BACKUP_DIR": "/opt/reporter/.backup",
        }

    context = _context(is_standalone_install=True, is_db_configured=False)
    values = collect_backup_values({}, prompt_fields, ask_select, context)

    assert values["BACKUP_CONFIG"] == "true,all,720,5"
    assert ask_calls == ["Should backup of the databases be enabled?"]


def test_collect_backup_values_disables_when_enable_backup_is_no() -> None:
    def ask_select(
        prompt: str,
        options: list[tuple[str, str]],
        default_value: str,
    ) -> str:
        return "no"

    context = _context(is_standalone_install=True, is_db_configured=False)
    values = collect_backup_values({}, lambda fields, defaults: {}, ask_select, context)

    assert values["BACKUP_CONFIG"].startswith("false,")
    assert values["BACKUP_DIR"] == default_backup_dir()
