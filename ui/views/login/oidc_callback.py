"""Callback-stage helpers for user resolution/provisioning and session finalize."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable, MutableMapping
    from logging import Logger


class QueryParamsLike(Protocol):
    """Minimal query-params API required from Streamlit objects."""

    def clear(self) -> None: ...


class StreamlitLike(Protocol):
    """Subset of Streamlit runtime methods used in callback helpers."""

    session_state: MutableMapping[str, object]
    query_params: QueryParamsLike

    def error(self, *args: object, **kwargs: object) -> None: ...
    def info(self, *args: object, **kwargs: object) -> None: ...
    def rerun(self) -> None: ...
    def switch_page(self, page: str) -> None: ...


class SessionManagerLike(Protocol):
    """Subset of session manager behavior needed in callback finalize."""

    def start_session(self, **kwargs: object) -> str: ...
    def get_session_token(self) -> str | None: ...


def resolve_or_provision_user(
    *,
    st_module: StreamlitLike,
    provider_name: str,
    claims: dict[str, object],
    username: str,
    mapped_group: tuple[int, str] | None,
    auto_provision_enabled: Callable[[], bool],
    auto_provision_require_email: Callable[[], bool],
    allowed_email_domains: Callable[[], set[str]],
    is_email_allowed: Callable[[str], bool],
    resolve_default_user_group: Callable[[], tuple[int, str]],
    resolve_display_name: Callable[[dict[str, object], str], str],
    clear_oidc_callback_state: Callable[[], None],
    create_oidc_user_fn: Callable[..., tuple[bool, str]],
    get_user_for_login_fn: Callable[[str], dict[str, object] | None],
    log: Logger,
    log_flow_step: Callable[..., None],
) -> dict[str, object] | None:
    """Resolve existing local user or auto-provision one, with UI redirects on failure."""
    user_row = get_user_for_login_fn(username)
    if user_row is None:
        if not auto_provision_enabled():
            log.error("User not found in Reporter DB and auto-provision disabled")
            clear_oidc_callback_state()
            st_module.error("You do not have a Reporter account.")
            log_flow_step(10, "user missing and auto-provision disabled -> redirect login", branch="A")
            st_module.switch_page("pages/_0_Login.py")
            return None

        email = str(claims.get("email", "")).strip().lower()
        if auto_provision_require_email() and not email:
            log.error("OIDC auto-provision denied reason=missing_email")
            clear_oidc_callback_state()
            st_module.error("Your identity provider did not provide an email address.")
            log_flow_step(10, "auto-provision denied missing email -> redirect login", branch="B")
            st_module.switch_page("pages/_0_Login.py")
            return None

        if not email and allowed_email_domains():
            log.error(
                "OIDC auto-provision denied reason=missing_email_for_allowlist allowed_domains=%s",
                sorted(allowed_email_domains()),
            )
            clear_oidc_callback_state()
            st_module.error("Your identity provider did not provide an email address.")
            log_flow_step(10, "auto-provision denied missing email for allowlist -> redirect login", branch="C")
            st_module.switch_page("pages/_0_Login.py")
            return None

        if not is_email_allowed(email):
            log.error(
                "OIDC auto-provision denied reason=domain_allowlist allowed_domains=%s",
                sorted(allowed_email_domains()),
            )
            clear_oidc_callback_state()
            st_module.error("Your account is not allowed for auto-provisioning.")
            log_flow_step(10, "auto-provision denied domain allowlist -> redirect login", branch="D")
            st_module.switch_page("pages/_0_Login.py")
            return None

        try:
            if mapped_group is not None:
                group_id, group_name = mapped_group
                log.info(
                    "OIDC auto-provision group selected from mapping group=%s(%s)",
                    group_name,
                    group_id,
                )
            else:
                group_id, group_name = resolve_default_user_group()
                log.info(
                    "OIDC auto-provision group selected from default role group=%s(%s)",
                    group_name,
                    group_id,
                )
            display_name = resolve_display_name(claims, username)
            success, message = create_oidc_user_fn(
                name=username,
                display_name=display_name,
                user_group_id=group_id,
                has_profile=True,
            )

            user_row = get_user_for_login_fn(username)
            if not success and user_row is None:
                log.error("OIDC auto-provision failed reason=%s", message)
                clear_oidc_callback_state()
                st_module.error("Failed to auto-provision local account.")
                log_flow_step(10, "auto-provision create failed -> redirect login", branch="E")
                st_module.switch_page("pages/_0_Login.py")
                return None

            if user_row is None:
                log.error("OIDC auto-provision completed but user lookup failed")
                clear_oidc_callback_state()
                st_module.error("Failed to finalize auto-provisioned account.")
                log_flow_step(10, "auto-provision lookup failed -> redirect login", branch="F")
                st_module.switch_page("pages/_0_Login.py")
                return None

                log.info(
                    "OIDC auto-provision success display_name_present=%s group=%s(%s) has_email=%s has_subject=%s",
                    bool(display_name),
                    group_name,
                    group_id,
                    bool(email),
                    bool(claims.get("sub")),
                )
        except Exception as provision_exc:
            log.exception("OIDC auto-provision exception")
            clear_oidc_callback_state()
            st_module.error(f"Failed to auto-provision local account: {provision_exc}")
            log_flow_step(10, "auto-provision exception -> redirect login", branch="G")
            st_module.switch_page("pages/_0_Login.py")
            return None
    elif mapped_group is not None:
        log.info(
            "OIDC group mapping resolved but existing local users are not altered; "
            "current_group=%s(%s) mapped_group=%s(%s)",
            user_row.get("group_name"),
            user_row.get("user_group_id"),
            mapped_group[1],
            mapped_group[0],
        )

    log.info("Matched Reporter user id=%s username_present=%s", user_row.get("id"), bool(user_row.get("name")))
    log_flow_step(10, "local user resolved user_id=%s", user_row.get("id"))
    return user_row


def persist_oidc_session(
    *,
    st_module: StreamlitLike,
    provider_name: str,
    token_response: dict[str, object],
    claims: dict[str, object],
    user_row: dict[str, object],
    oidc_id_token_key: str,
    oidc_access_token_key: str,
    oidc_refresh_token_key: str,
    oidc_expires_at_key: str,
    oidc_refresh_expires_at_key: str,
    oidc_id_token_exp_key: str,
    seconds_left: Callable[[float | datetime | None], int | None],
    preview: Callable[[object | None], str],
    session_state_oidc_summary: Callable[[], dict[str, object]],
    clear_oidc_callback_state: Callable[[], None],
    authenticated_key: str,
    hydrate_authenticated_state_fn: Callable[[dict[str, object]], None],
    session_manager_obj: SessionManagerLike,
    log: Logger,
    log_flow_step: Callable[..., None],
) -> bool:
    """Persist OIDC/session state and complete redirect when cookie is visible."""
    id_token = token_response.get("id_token")
    now_ts = int(time.time())
    expires_in = int(token_response.get("expires_in", 0))
    refresh_expires_in = int(token_response.get("refresh_expires_in", 0))
    id_token_exp = int(claims.get("exp", 0))

    st_module.session_state["auth_source"] = f"oidc:{provider_name}"
    st_module.session_state[oidc_id_token_key] = str(id_token) if id_token else None
    st_module.session_state[oidc_access_token_key] = token_response.get("access_token")
    st_module.session_state[oidc_refresh_token_key] = token_response.get("refresh_token")
    st_module.session_state[oidc_expires_at_key] = now_ts + expires_in if expires_in > 0 else None
    st_module.session_state[oidc_refresh_expires_at_key] = (
        now_ts + refresh_expires_in if refresh_expires_in > 0 else None
    )
    st_module.session_state[oidc_id_token_exp_key] = id_token_exp if id_token_exp > 0 else None

    log.info(
        "Session-state OIDC values set access_expires_in=%s refresh_expires_in=%s id_token_exp_in=%s",
        seconds_left(st_module.session_state.get(oidc_expires_at_key)),
        seconds_left(st_module.session_state.get(oidc_refresh_expires_at_key)),
        seconds_left(st_module.session_state.get(oidc_id_token_exp_key)),
    )

    hydrate_authenticated_state_fn(user_row)
    access_expires_at = datetime.fromtimestamp(now_ts + expires_in, tz=UTC) if expires_in > 0 else None
    refresh_expires_at = datetime.fromtimestamp(now_ts + refresh_expires_in, tz=UTC) if refresh_expires_in > 0 else None

    session_token = session_manager_obj.start_session(
        user_id=user_row["id"],
        auth_source=f"oidc:{provider_name}",
        oidc_access_token=token_response.get("access_token"),
        oidc_refresh_token=token_response.get("refresh_token"),
        oidc_access_expires_at=access_expires_at,
        oidc_refresh_expires_at=refresh_expires_at,
        oidc_id_token=str(id_token) if id_token else None,
    )

    log.info(
        "Reporter session started authenticated=%s auth_source=%s session_token_present=%s",
        st_module.session_state.get(authenticated_key, False),
        st_module.session_state.get("auth_source"),
        bool(session_token),
    )
    log_flow_step(11, "reporter session started")

    cookie_token = session_manager_obj.get_session_token()
    log.info(
        "Cookie/session comparison cookie_present=%s session_token_present=%s match=%s",
        bool(cookie_token),
        bool(session_token),
        cookie_token == session_token,
    )
    log_flow_step(12, "checking session cookie persistence")

    if cookie_token != session_token:
        log.info(
            "Waiting for session cookie to persist before redirecting cookie_present=%s session_token_present=%s",
            bool(cookie_token),
            bool(session_token),
        )
        st_module.info("Finalizing sign-in...")
        st_module.query_params.clear()
        log_flow_step(12, "session cookie not persisted yet -> rerun", branch="A")
        st_module.rerun()
        return False

    log.info("Session cookie persisted, redirecting to home")
    log.info("Before switch_page state summary: %s", session_state_oidc_summary())
    clear_oidc_callback_state()
    log_flow_step(13, "login complete -> redirect home")
    st_module.switch_page("pages/_1_Home.py")
    return True
