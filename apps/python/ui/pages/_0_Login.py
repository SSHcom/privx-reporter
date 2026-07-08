from __future__ import annotations

import streamlit as st
from streamlit.logger import get_logger

import ui.constants as constants
from ui.db.user_queries import get_user_for_login
from ui.services.page_bootstrap import setup_page
from ui.services.session import keys, session_manager
from ui.services.session.state import hydrate_authenticated_state, init_session_state
from ui.utils.password import validate_password
from lib.service.env_source import reloadEnv
from lib import env_oidc
from ui.views.login import (
    clear_oidc_auth_state,
    complete_oidc_login,
    has_oidc_callback_params,
    render_oidc_login,
)

logger = get_logger(__name__)


def _log_oidc_flow_step(step: int, message: str, *args: object, branch: str | None = None) -> None:
    branch_suffix = branch.strip().upper() if branch else ""
    logger.info(f"OIDC FLOW STEP %02d{branch_suffix}: " + message, step, *args)


def _setup_callback_page() -> None:
    """Bootstrap callback page without restore_session side effects."""
    st.set_page_config(page_title=constants.APP_TITLE, layout="centered", page_icon=constants.APP_FAVICON)
    st.markdown(constants.PAGE_STYLE, unsafe_allow_html=True)
    init_session_state()
    # Deliberately avoid session_manager.init() here. Callback handling must run
    # first, and start_session() now initializes cookie storage on demand.


def _preview(value: object) -> str:
    if value is None:
        return "<none>"
    s = str(value)
    return s if len(s) <= 10 else f"{s[:6]}...{s[-4:]}"


def _get_enabled_oidc_providers() -> list[str]:
    """Return list of enabled OIDC provider slots (e.g. ['1', '2'])."""
    providers = [str(slot) for slot in env_oidc.get_enabled_slots()]
    logger.info("Enabled OIDC providers=%s", providers)
    return providers


def _render_local_login(*, show_info: bool = True) -> None:
    logger.info("Rendering local login form")
    if show_info:
        st.info("Sign in using local credentials.")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", width="stretch")

    if not submitted:
        logger.info("Local login not submitted")
        return

    normalized_username = username.strip()
    password_is_empty = not password.strip()

    if not normalized_username or password_is_empty:
        logger.info("Local login rejected reason=missing_credentials username=%s", _preview(normalized_username))
        st.error("Please enter both username and password.")
        return

    user = get_user_for_login(normalized_username)
    if user is None or not validate_password(password, user["encrypted_password"]):
        logger.info("Local login rejected reason=invalid_credentials username=%s", _preview(normalized_username))
        st.error("Invalid username or password.")
        return

    st.session_state["auth_source"] = "local"
    clear_oidc_auth_state(clear_query_params=False)
    hydrate_authenticated_state(user)
    session_manager.start_session(user_id=user["id"], auth_source="local")
    logger.info("Local login success user_id=%s username=%s", user["id"], user.get("name"))
    st.switch_page("pages/_1_Home.py")


def main() -> None:
    reloadEnv()
    logger.info(
        "Login page start query_keys=%s has_code=%s has_state=%s error=%s",
        sorted(st.query_params.keys()),
        bool(st.query_params.get("code")),
        bool(st.query_params.get("state")),
        st.query_params.get("error"),
    )
    # Handle OIDC callback as early as possible. `setup_page()` calls `restore_session()`,
    # and Streamlit reruns can otherwise re-enter before callback processing starts.
    if has_oidc_callback_params():
        logger.info("Login page routing branch=oidc_callback")
        _log_oidc_flow_step(1, "callback params detected on login page -> processing callback", branch="A")
        _setup_callback_page()
        complete_oidc_login()
        return

    logger.info("Login page routing branch=interactive_login")
    setup_page(page_title=constants.APP_TITLE, layout="centered", require_login=False)

    if st.session_state.get(keys.AUTHENTICATED, False):
        logger.info("Login page: already authenticated -> redirecting home")
        _log_oidc_flow_step(13, "already authenticated on login page -> redirect home", branch="A")
        st.switch_page("pages/_1_Home.py")

    with st.sidebar:
        st.image("components/logo.png", width=220)

    st.title(constants.APP_TITLE)

    oidc_providers = _get_enabled_oidc_providers()
    collapse_local = env_oidc.env_flag("UI_COLLAPSE_LOCAL_LOGIN", default=False) and oidc_providers

    if collapse_local:
        st.info("Sign in using your Identity Provider.")
        for provider in oidc_providers:
            logger.info("Rendering OIDC login button provider=%s", provider)
            render_oidc_login(provider)
        with st.expander("Sign in with local credentials"):
            _render_local_login(show_info=False)
    else:
        _render_local_login()
        if oidc_providers:
            st.write("---")
            st.info("Sign in using your Identity Provider.")
            for provider in oidc_providers:
                logger.info("Rendering OIDC login button provider=%s", provider)
                render_oidc_login(provider)


main()
