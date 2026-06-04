"""
Environment variable configuration module.
Only add environment variables that are used in multiple modules.

Example: Sync server needs sync retention days that is not needed
         elsewhere. Don't include it here.

Tests are not necessary for this module.
"""

import os


class EnvConfig:
    """Misc configuration"""

    @staticmethod
    def get_api_batchsize() -> int:
        """Get API batch size from environment variable."""
        return int(os.getenv("REPORT_API_BATCH_SIZE", "100"))

    @staticmethod
    def get_report_out_dir() -> str:
        """Get report output directory path from environment variable."""
        return os.getenv("REPORT_OUT_DIR", "report_out")

    """Database configuration"""

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
        return os.getenv("PRIVX_API_OAUTH_CLIENT_ID", "")

    @staticmethod
    def get_privx_api_oauth_client_secret() -> str:
        """Get PrivX API OAuth client secret from environment variable."""
        return os.getenv("PRIVX_API_OAUTH_CLIENT_SECRET", "")

    @staticmethod
    def get_privx_api_client_id() -> str:
        """Get PrivX API client ID from environment variable."""
        return os.getenv("PRIVX_API_CLIENT_ID", "")

    @staticmethod
    def get_privx_api_client_secret() -> str:
        """Get PrivX API client secret from environment variable."""
        return os.getenv("PRIVX_API_CLIENT_SECRET", "")

    @staticmethod
    def get_privx_ca_cert() -> str:
        """Get path to PrivX CA certificate from environment variable."""
        return os.getenv("PRIVX_CA_CERT", "")

    @staticmethod
    def get_privx_hostname() -> str:
        """Get PrivX hostname from environment variable."""
        return os.getenv("PRIVX_HOSTNAME", "localhost")

    @staticmethod
    def get_privx_port() -> int:
        """Get PrivX port from environment variable."""
        return int(os.getenv("PRIVX_PORT", "443"))

    """UI authentication configuration"""

    @staticmethod
    def get_ui_oidc_enabled() -> bool:
        """Enable optional OIDC login flow for Streamlit UI authentication."""
        return os.getenv("UI_OIDC_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def get_ui_oidc_provider() -> str:
        """Get optional provider identifier used by Streamlit ``st.login``."""
        return os.getenv("UI_OIDC_PROVIDER", "").strip()

    @staticmethod
    def get_ui_oidc_username_claim() -> str:
        """Get OIDC claim name that maps to local ``user.name`` values."""
        return os.getenv("UI_OIDC_USERNAME_CLAIM", "email").strip() or "email"
