from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from os import PathLike
from pathlib import Path
from typing import Protocol, cast

from lib._shared.helpers import repo_root
from lib.interactive.env import (
    DEFAULT_OVERRIDES,
    OUTPUT_GROUPS,
    OUTPUT_ORDER,
    FieldDef,
    collect_env_values,
)

DotenvValues = Callable[[str | PathLike[str] | None], dict[str, str | None]]
dotenv_values: DotenvValues | None
try:
    from dotenv import dotenv_values as _loaded_dotenv_values

    dotenv_values = _loaded_dotenv_values
except ImportError:  # pragma: no cover - handled with runtime check
    dotenv_values = None


class _QuestionaryPrompt(Protocol):
    def ask(self) -> object | None: ...


class _QuestionaryModule(Protocol):
    def text(self, message: str, default: str = "") -> _QuestionaryPrompt: ...

    def select(
        self,
        message: str,
        choices: list[str],
        default: str | None = None,
    ) -> _QuestionaryPrompt: ...

    def confirm(self, message: str, default: bool = True) -> _QuestionaryPrompt: ...


questionary: _QuestionaryModule | None
try:
    import questionary as _loaded_questionary

    questionary = cast("_QuestionaryModule", _loaded_questionary)
except ImportError:  # pragma: no cover - handled with fallback prompts
    questionary = None

type SelectOptions = list[tuple[str, str]]
type SectionModeArg = str | None


def parse_env_defaults(template_path: Path) -> dict[str, str]:
    if dotenv_values is None:
        raise RuntimeError("python-dotenv is required. Install it to parse .env-example values.")

    defaults: dict[str, str] = {}
    valid_keys = set(OUTPUT_ORDER)
    parsed_values = dotenv_values(template_path)
    for key, value in parsed_values.items():
        if key not in valid_keys:
            continue
        defaults[key] = value if value is not None else ""

    for key, value in DEFAULT_OVERRIDES.items():
        defaults.setdefault(key, value)
    return defaults


def is_questionary_available() -> bool:
    return questionary is not None and sys.stdin.isatty() and sys.stdout.isatty()


def ask_text(prompt: str, default: str) -> str:
    if is_questionary_available():
        q = questionary
        if q is None:
            raise RuntimeError("questionary is unexpectedly unavailable")
        result = cast("str | None", q.text(prompt, default=default).ask())
        if result is None:
            raise KeyboardInterrupt
        return result.strip()
    entered = input(f"{prompt} [{default}]: ").strip()
    return entered or default


def ask_select(prompt: str, options: SelectOptions, default_value: str) -> str:
    option_labels = [label for _, label in options]
    default_label = next(label for value, label in options if value == default_value)
    if is_questionary_available():
        q = questionary
        if q is None:
            raise RuntimeError("questionary is unexpectedly unavailable")
        result = q.select(prompt, choices=option_labels, default=default_label).ask()
        if result is None:
            raise KeyboardInterrupt
        for value, label in options:
            if label == result:
                return value
        raise ValueError("Unknown select result")

    print(prompt)
    for idx, (value, label) in enumerate(options, start=1):
        marker = " (default)" if value == default_value else ""
        print(f"  {idx}. {label}{marker}")
    while True:
        entered = input("Select option number: ").strip()
        if not entered:
            return default_value
        if entered.isdigit():
            index = int(entered) - 1
            if 0 <= index < len(options):
                return options[index][0]
        print("Please enter a valid option number.")


def ask_confirm(prompt: str, default: bool = True) -> bool:
    if is_questionary_available():
        q = questionary
        if q is None:
            raise RuntimeError("questionary is unexpectedly unavailable")
        result = cast("bool | None", q.confirm(prompt, default=default).ask())
        if result is None:
            raise KeyboardInterrupt
        return result
    suffix = "Y/n" if default else "y/N"
    while True:
        entered = input(f"{prompt} [{suffix}]: ").strip().lower()
        if not entered:
            return default
        if entered in {"y", "yes"}:
            return True
        if entered in {"n", "no"}:
            return False
        print("Please answer yes or no.")


def prompt_field(field: FieldDef, defaults: dict[str, str]) -> str:
    default_value = defaults.get(field.key, "")
    while True:
        print(f"\n{field.key}: {field.description}")
        answer = ask_text(field.label, default_value)
        is_valid, message = field.validator(answer.strip())
        if is_valid:
            return answer.strip()
        print(f"Invalid value: {message}")


def prompt_fields(fields: list[FieldDef], defaults: dict[str, str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in fields:
        values[field.key] = prompt_field(field, defaults)
    return values


def choose_output_path(default_path: str) -> Path:
    print("\nOutput file: where generated environment settings are written.")
    selected = ask_text("Output .env path", default_path).strip()
    if not selected:
        selected = default_path
    return Path(selected).expanduser()


def resolve_default_output_path(output_arg: str) -> str:
    output_path = Path(output_arg).expanduser()
    if output_path.is_absolute():
        return str(output_path)
    return str((repo_root() / output_path).resolve())


def format_env_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    if value.isdigit():
        return value
    return f'"{escaped}"'


def render_env(values: dict[str, str]) -> str:
    grouped_blocks = []
    for group in OUTPUT_GROUPS:
        group_lines = [f"{key}={format_env_value(values[key])}" for key in group if key in values]
        if not group_lines:
            continue
        grouped_blocks.append("\n".join(group_lines))
    return "\n\n".join(grouped_blocks) + "\n"


def print_summary(values: dict[str, str], output_path: Path) -> None:
    print("\nSummary of values to be written:")
    for key in OUTPUT_ORDER:
        if key in values:
            print(f"  {key}={values[key]}")
    print(f"\nTarget file: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactively create a .env file for DB/report/PrivX settings.")
    parser.add_argument(
        "--output",
        default=".env",
        help="Default output path used as pre-filled value in prompt (default: .env).",
    )
    parser.add_argument(
        "--db",
        choices=["defaults", "skip"],
        help=(
            "Database section mode: defaults=use .env-example values without prompting, "
            "skip=omit DB values from output."
        ),
    )
    parser.add_argument(
        "--sync",
        choices=["defaults", "skip"],
        help=(
            "Sync section mode: defaults=use .env-example values without prompting, "
            "skip=omit SYNC_* values from output."
        ),
    )
    parser.add_argument(
        "--ui",
        choices=["defaults", "skip"],
        help=(
            "UI section mode: defaults=use .env-example values (still prompts for UI_TMP_ADMIN_PASSWORD), "
            "skip=omit UI_* values from output."
        ),
    )
    args = parser.parse_args()

    template_path = repo_root() / ".env-example"
    if not template_path.exists():
        print(f"Template file not found: {template_path}", file=sys.stderr)
        return 1

    try:
        defaults = parse_env_defaults(template_path)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    try:
        default_output_path = resolve_default_output_path(args.output)
        output_path = choose_output_path(default_output_path)
        db_mode: SectionModeArg = args.db
        sync_mode: SectionModeArg = args.sync
        ui_mode: SectionModeArg = args.ui
        values = collect_env_values(
            defaults,
            prompt_fields,
            ask_select,
            db_mode=db_mode or "ask",
            sync_mode=sync_mode or "ask",
            ui_mode=ui_mode or "ask",
        )

        print_summary(values, output_path)
        if not ask_confirm("Write these values to file?", default=True):
            print("Cancelled: no file written.")
            return 0

        if output_path.exists() and not ask_confirm(f"{output_path} exists. Overwrite it?", default=False):
            print("Cancelled: existing file kept unchanged.")
            return 0

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(render_env(values), encoding="utf-8")
        print(f"Wrote configuration to {output_path}")
        return 0
    except ValueError as error:
        if args.db == "defaults" or args.sync == "defaults" or args.ui == "defaults":
            print(str(error), file=sys.stderr)
            return 1
        raise
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
