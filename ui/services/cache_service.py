import logging

import privx_api.exceptions
import streamlit as st
from streamlit.logger import get_logger

from lib.clients.privx import clear_privx_client_cache, get_privx_client


@st.cache_resource
def get_cached_privx_client() -> privx_api.PrivXAPI:
    """
    Get cached PrivX API client.
    Note: If authentication fails, you may need to clear Streamlit's cache
    by clicking the "Clear cache" button in the Streamlit menu, or by
    restarting the Streamlit server.
    """
    try:
        return get_privx_client()
    except (privx_api.exceptions.InternalAPIException, Exception):
        # Clear module-level cache on authentication failure
        clear_privx_client_cache()
        # Don't cache authentication failures - re-raise to let user know
        # User can clear Streamlit cache manually via Streamlit UI or restart server
        raise


@st.cache_resource
def get_cached_logger() -> logging.Logger:
    return get_logger(__name__)
