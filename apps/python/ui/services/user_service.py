from __future__ import annotations

import streamlit as st
from streamlit.logger import get_logger

from lib.report_api import roles as roles_api
from ui.services.cache_service import get_cached_privx_client
from ui.services.session import keys

logger = get_logger(__name__)

def _normalize(value: object) -> str:
    return str(value or "").strip().casefold()


def _find_matching_users(username: str) -> list[dict[str, str]]:
    api = get_cached_privx_client()

    users = roles_api.get_all_users(
        api,
        search_payload={},
        sort_key="principal",
        sort_dir="asc",
    )

    response_count = len(users)

    logger.info(
        "PrivX get_all_users returned records response_count=%s items_count=%s",
        response_count,
        len(users),
    )

    # Skip machine/API users from identity matching.
    users = [user for user in users if _normalize(user.get("source_type")) != "api-client"]
    logger.info("PrivX user records after source_type filter count=%s", len(users))

    username_norm = _normalize(username)
    exact_matches = [
        user
        for user in users
        if username_norm == _normalize(user.get("principal"))
    ]

    exact_matches = [
        user for user in exact_matches if str(user.get("id", "")).strip()
    ]

    matches = [
        {
            "id": str(user.get("id", "")).strip(),
            "principal": str(user.get("principal", "")).strip(),
            "source_type": str(user.get("source_type", "")).strip(),
        }
        for user in exact_matches
    ]
    matches.sort(key=lambda item: (item["source_type"].casefold(), item["id"]))
    return matches


def get_privx_user_matches(username: str) -> list[dict[str, str]]:
    """Resolve and cache all PrivX users whose principal matches username."""
    cached_username = st.session_state.get(keys.PRIVX_USER_LOOKUP_USERNAME)
    lookup_done = st.session_state.get(keys.PRIVX_USER_LOOKUP_DONE) is True

    if lookup_done and cached_username == username:
        cached_matches = st.session_state.get(keys.PRIVX_USER_MATCHES)
        logger.debug(
            "PrivX user lookup cache hit username=%s resolved_count=%s",
            username,
            len(cached_matches) if isinstance(cached_matches, list) else 0,
        )
        if not isinstance(cached_matches, list):
            return []
        return [match for match in cached_matches if isinstance(match, dict)]

    try:
        matches = _find_matching_users(username)
    except Exception:
        logger.exception("Failed to resolve PrivX user matches for username=%s", username)
        matches = []

    user_ids: list[str] = []
    seen_user_ids: set[str] = set()
    for match in matches:
        user_id = str(match.get("id", "")).strip()
        if not user_id or user_id in seen_user_ids:
            continue
        seen_user_ids.add(user_id)
        user_ids.append(user_id)

    logger.info(
        "PrivX user lookup completed username=%s resolved_count=%s",
        username,
        len(user_ids),
    )
    st.session_state[keys.PRIVX_USER_LOOKUP_USERNAME] = username
    st.session_state[keys.PRIVX_USER_LOOKUP_DONE] = True
    st.session_state[keys.PRIVX_USER_IDS] = user_ids
    st.session_state[keys.PRIVX_USER_MATCHES] = matches
    st.session_state[keys.PRIVX_USER_ID] = user_ids[0] if user_ids else None
    return matches


def get_privx_user_ids(username: str) -> list[str]:
    """Resolve all PrivX user IDs whose principal matches username."""
    return [
        str(match.get("id", ""))
            .strip() for match in get_privx_user_matches(username) if str(match.get("id", "")).strip()
    ]

def get_privx_user_id(username: str) -> str | None:
    """Resolve one matching PrivX user ID for compatibility callers."""
    user_ids = get_privx_user_ids(username)
    if not user_ids:
        return None
    return user_ids[0]
