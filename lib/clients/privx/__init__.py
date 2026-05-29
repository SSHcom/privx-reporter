# PrivX client initialization module
# Tests are not necessary for this module.

import privx_api
import privx_api.exceptions

from lib._report.error import ConfigError
from lib.env import EnvConfig

from .http_error import handle_http_5xx_error

# Module-level cache for the PrivX API client
_privx_client: privx_api.PrivXAPI | None = None


def clear_privx_client_cache() -> None:
    """Clear the module-level PrivX client cache."""
    global _privx_client
    _privx_client = None


def get_privx_client() -> privx_api.PrivXAPI:
    """
    Initialize and return an authenticated PrivXAPI client using environment variables.
    Uses caching to avoid recreating the client on each call.
    """
    global _privx_client

    if _privx_client is not None:
        return _privx_client

    hostname = EnvConfig.get_privx_hostname()
    port = EnvConfig.get_privx_port()
    ca_cert = EnvConfig.get_privx_ca_cert()
    oauth_client_id = EnvConfig.get_privx_api_oauth_client_id()
    oauth_client_secret = EnvConfig.get_privx_api_oauth_client_secret()
    api_client_id = EnvConfig.get_privx_api_client_id()
    api_client_secret = EnvConfig.get_privx_api_client_secret()

    # Validate that required credentials are provided
    if not api_client_id or not api_client_secret:
        raise ConfigError(
            "PrivX API client credentials are missing. "
            "Please set PRIVX_API_CLIENT_ID and PRIVX_API_CLIENT_SECRET environment variables.",
            "Check your .env file or environment variables.",
        )

    api = privx_api.PrivXAPI(
        hostname,
        port,
        ca_cert,
        oauth_client_id,
        oauth_client_secret,
    )

    try:
        api.authenticate(api_client_id, api_client_secret)
    except privx_api.exceptions.InternalAPIException as e:
        # Clear cache on authentication failure
        clear_privx_client_cache()
        handle_http_5xx_error(e, "PrivX API authentication")

    _privx_client = api
    return _privx_client
