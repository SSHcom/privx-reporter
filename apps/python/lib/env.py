"""
Environment variable configuration module.
Only add environment variables that are used in multiple modules.

Example: Sync server needs sync retention days that is not needed
         elsewhere. Don't include it here.

Tests are not necessary for this module.
"""

import os
from pathlib import Path

from lib.service.env_source import getEnv

REPORT_OUT_DIR = "REPORT_OUT_DIR"
REPORT_OUT_DIR_BASENAME = "REPORTS"


def default_report_out_dir() -> str:
    """Return the default report output directory under the current user's home directory."""
    return str(Path.home() / REPORT_OUT_DIR_BASENAME)


class EnvConfig:
    """Misc configuration"""

    @staticmethod
    def get_env_source() -> str:
        """Resolve configuration source selector ('env' or 'db')."""
        source = os.getenv("ENV_SOURCE", "env").strip().lower()
        if source not in {"env", "db"}:
            return "env"
        return source

    @staticmethod
    def get_api_batchsize() -> int:
        """Get API batch size from environment variable."""
        return int(getEnv("REPORT_API_BATCH_SIZE", "100"))

    @staticmethod
    def get_report_out_dir() -> str:
        """Get report output directory path from environment variable (always from env, never DB)."""
        return os.getenv(REPORT_OUT_DIR) or default_report_out_dir()

    """Database configuration.

    DB_* variables are always read from the process environment (os.getenv),
    even when ENV_SOURCE=db, so the admin database can be reached to load
    app config from the database.
    """

    @staticmethod
    def get_db_config() -> dict[str, dict[str, str | int | bool]]:
        """Get all database configuration grouped by logical database."""
        return {
            "data": EnvConfig.get_data_db_config(),
            "admin": EnvConfig.get_admin_db_config(),
        }

    @staticmethod
    def _get_db_instance_config(instance: str, default_port: str, default_name: str) -> dict[str, str | int | bool]:
        """Resolve a single logical DB connection config from prefixed env vars."""
        prefix = f"DB_{instance.upper()}_"
        return {
            "host": os.getenv(f"{prefix}HOST", "localhost"),
            "port": int(os.getenv(f"{prefix}PORT", default_port)),
            "user": os.getenv(f"{prefix}USER", "postgres"),
            "password": os.getenv(f"{prefix}PASSWORD", "postgres"),
            "name": os.getenv(f"{prefix}NAME", default_name),
            "ssl": os.getenv(f"{prefix}SSL_MODE", "off").lower() == "on",
        }

    @staticmethod
    def get_data_db_config() -> dict[str, str | int | bool]:
        """Get data database connection settings."""
        return EnvConfig._get_db_instance_config("data", "5444", "report_data")

    @staticmethod
    def get_admin_db_config() -> dict[str, str | int | bool]:
        """Get admin database connection settings."""
        return EnvConfig._get_db_instance_config("admin", "5445", "report_admin")

    """PrivX configuration"""

    @staticmethod
    def get_privx_config() -> dict[str, str]:
        return {
            "oauth_client_id": EnvConfig.get_privx_api_oauth_client_id(),
            "oauth_client_secret": EnvConfig.get_privx_api_oauth_client_secret(),
            "client_id": EnvConfig.get_privx_api_client_id(),
            "client_secret": EnvConfig.get_privx_api_client_secret(),
            "ca_cert": EnvConfig.get_privx_ca_cert(),
            "hostname": EnvConfig.get_privx_hostname(),
            "port": str(EnvConfig.get_privx_port()),
        }

    @staticmethod
    def get_privx_api_oauth_client_id() -> str:
        """Get PrivX API OAuth client ID from environment variable."""
        return getEnv("PRIVX_API_OAUTH_CLIENT_ID", "")

    @staticmethod
    def get_privx_api_oauth_client_secret() -> str:
        """Get PrivX API OAuth client secret from environment variable."""
        return getEnv("PRIVX_API_OAUTH_CLIENT_SECRET", "")

    @staticmethod
    def get_privx_api_client_id() -> str:
        """Get PrivX API client ID from environment variable."""
        return getEnv("PRIVX_API_CLIENT_ID", "")

    @staticmethod
    def get_privx_api_client_secret() -> str:
        """Get PrivX API client secret from environment variable."""
        return getEnv("PRIVX_API_CLIENT_SECRET", "")

    @staticmethod
    def get_privx_ca_cert() -> str:
        """Get path to PrivX CA certificate from environment variable."""
        return getEnv("PRIVX_CA_CERT", "")

    @staticmethod
    def get_privx_hostname() -> str:
        """Get PrivX hostname from environment variable."""
        return getEnv("PRIVX_HOSTNAME", "localhost")

    @staticmethod
    def get_privx_port() -> int:
        """Get PrivX port from environment variable."""
        return int(getEnv("PRIVX_PORT", "443"))
