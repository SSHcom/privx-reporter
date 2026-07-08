"""Resolve environment values from process env or app-config DB."""

from __future__ import annotations

import os
from typing import overload


class EnvSource:
    """Lookup helper with lazy-loaded DB values."""

    def __init__(self) -> None:
        self._db_values: dict[str, str] | None = None

    def _read_db_values(self) -> dict[str, str]:
        if self._db_values is not None:
            return self._db_values

        # Prevent reentrant loads while establishing the admin DB connection.
        self._db_values = {}
        try:
            from lib.database.app_config_db import read_all_app_config_values

            self._db_values = read_all_app_config_values()
        except Exception:
            self._db_values = {}
        return self._db_values

    def reload_db_values(self) -> None:
        """Clear cached DB values so next get_env() re-reads from database."""
        self._db_values = None

    def get_env(self, env_var: str, default: str | None = None) -> str | None:
        source = os.getenv("ENV_SOURCE", "env").strip().lower()
        if source != "db":
            return os.getenv(env_var, default)

        db_value = self._read_db_values().get(env_var)
        if db_value is not None:
            return db_value

        env_value = os.getenv(env_var)
        if env_value is not None:
            return env_value

        return default


_env_source = EnvSource()


@overload
def getEnv(env_var: str, default: str) -> str: ...


@overload
def getEnv(env_var: str, default: None = None) -> str | None: ...


def getEnv(env_var: str, default: str | None = None) -> str | None:  # noqa: N802
    """Read a config value from selected source."""
    return _env_source.get_env(env_var, default)


def reloadEnv() -> None:  # noqa: N802
    """Clear cached DB values so next getEnv() call re-reads from database."""
    _env_source.reload_db_values()
