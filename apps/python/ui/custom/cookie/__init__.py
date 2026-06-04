import datetime as dt
import os
from collections.abc import Mapping
from typing import Literal
from urllib.parse import urlparse

import streamlit as st
import streamlit.components.v1 as components
from streamlit.logger import get_logger

CookieValue = str | int | float | bool
CookieJar = dict[str, CookieValue]

logger = get_logger(__name__)


def _resolve_dev_server_url() -> str | None:
    """Return a normalized dev-server URL or None when invalid/missing."""
    raw = os.getenv("COOKIE_COMPONENT_DEV_URL")
    if raw is None:
        return None

    candidate = raw.strip().strip("'").strip('"')
    if not candidate:
        return None

    # Accept host:port input by adding a default scheme.
    if "://" not in candidate:
        candidate = f"http://{candidate}"

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        logger.warning(
            "Ignoring invalid COOKIE_COMPONENT_DEV_URL=%r; using bundled cookie component build.",
            raw,
        )
        return None

    return candidate


_DEV_SERVER_URL = _resolve_dev_server_url()
_COMPONENT_NAME = "custom_cookie_manager"
_BUILD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend/build")

if _DEV_SERVER_URL:
    _component_func = components.declare_component(_COMPONENT_NAME, url=_DEV_SERVER_URL)
else:
    _component_func = components.declare_component(_COMPONENT_NAME, path=_BUILD_DIR)


class CookieManager:
    def __init__(self, key: str = "cookie_manager_init") -> None:
        self._cookie_manager = _component_func
        self.cookies = self.get_all(key=key)

    def get(self, cookie: str) -> CookieValue | None:
        self._hide_component_iframe()
        return self.cookies.get(cookie)

    def set(
        self,
        cookie: str,
        value: CookieValue,
        key: str = "cookie_set",
        path: str = "/",
        expires_at: dt.datetime | None = None,
        max_age: float | None = None,
        domain: str | None = None,
        secure: bool | None = None,
        same_site: Literal["lax", "strict", "none"] | None = "strict",
    ) -> None:
        if not cookie:
            return

        if expires_at is None:
            expires_at = dt.datetime.now(dt.UTC) + dt.timedelta(days=1)

        options: dict[str, str | float | bool] = {
            "path": path,
            "expires": expires_at.isoformat(),
        }
        if max_age is not None:
            options["maxAge"] = max_age
        if domain is not None:
            options["domain"] = domain
        if secure is not None:
            options["secure"] = secure
        if same_site is not None:
            options["sameSite"] = same_site

        self._hide_component_iframe()
        self._cookie_manager(
            method="set",
            cookie=cookie,
            value=value,
            options=options,
            key=key,
            default=False,
        )
        self.cookies[cookie] = value

    def batch_set(
        self,
        cookies: Mapping[str, CookieValue],
        path: str = "/",
        expires_at: dt.datetime | None = None,
        max_age: float | None = None,
        domain: str | None = None,
        secure: bool | None = None,
        same_site: Literal["lax", "strict", "none"] | None = "strict",
    ) -> None:
        for idx, (cookie, value) in enumerate(cookies.items()):
            self.set(
                cookie=cookie,
                value=value,
                key=f"cookie_set_{idx}",
                path=path,
                expires_at=expires_at,
                max_age=max_age,
                domain=domain,
                secure=secure,
                same_site=same_site,
            )

    def delete(
        self,
        cookie: str,
        key: str = "cookie_delete",
        path: str = "/",
        domain: str | None = None,
    ) -> None:
        if not cookie:
            return

        self._cookie_manager(
            method="delete",
            cookie=cookie,
            options={"path": path, "domain": domain} if domain else {"path": path},
            key=key,
            default=False,
        )
        self.cookies.pop(cookie, None)

    def get_all(self, key: str = "cookie_get_all") -> CookieJar:
        self._hide_component_iframe()
        cookies = self._cookie_manager(method="getAll", key=key, default={})
        self.cookies = cookies or {}
        return self.cookies

    @staticmethod
    def _hide_component_iframe() -> None:
        st.markdown(
            """
            <style>
                .element-container:has(iframe[height="0"]) { display: none; }
            </style>
            """,
            unsafe_allow_html=True,
        )


__all__ = ["CookieManager", "CookieValue"]
