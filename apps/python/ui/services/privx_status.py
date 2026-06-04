from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError

from lib.clients.privx import clear_privx_client_cache, get_privx_client
from ui.services.cache_service import get_cached_privx_client

_PRIVX_CHECK_TIMEOUT_SECONDS = 3.0


def _clear_privx_caches() -> None:
    """Clear both module-level and Streamlit resource caches for PrivX client."""
    clear_privx_client_cache()
    get_cached_privx_client.clear()


def get_privx_connection_error() -> str | None:
    """Return a user-facing error message when PrivX connection cannot be established."""
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(get_privx_client)
        future.result(timeout=_PRIVX_CHECK_TIMEOUT_SECONDS)
        return None
    except TimeoutError:
        _clear_privx_caches()
        future.cancel()
        return f"PrivX connection issue: connection check timed out after {int(_PRIVX_CHECK_TIMEOUT_SECONDS)}s."
    except SystemExit:
        _clear_privx_caches()
        return "PrivX connection issue: cannot connect to PrivX. Check PRIVX_HOSTNAME and network reachability."
    except Exception as exc:
        _clear_privx_caches()
        return f"PrivX connection issue: {exc}"
    finally:
        # Do not block page rendering on a hung network call.
        pool.shutdown(wait=False, cancel_futures=True)
