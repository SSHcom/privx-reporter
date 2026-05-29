"""Static OIDC provider/config helpers used by login rendering and callback flow."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from streamlit.logger import get_logger

log = get_logger(__name__)
_ICON_FILES: dict[str, str] = {
    "keycloak": "keycloak.svg",
    "entra": "entra.svg",
}
_ICONS_DIR = Path(__file__).resolve().parents[2] / "assets" / "icons"


def get_oidc_config(provider_name: str) -> dict[str, str]:
    """Load required OIDC environment configuration."""
    provider = str(provider_name or "").strip()
    if not provider or provider.lower() == "oidc":
        raise ValueError("Deprecated OIDC provider id 'oidc'. Use a named provider and set <PROVIDER>_OIDC_* vars.")

    prefix = f"{provider.upper()}_"
    return {
        "issuer": os.environ[f"{prefix}OIDC_ISSUER"].rstrip("/"),
        "client_id": os.environ[f"{prefix}OIDC_CLIENT_ID"],
        "client_secret": os.environ[f"{prefix}OIDC_CLIENT_SECRET"],
        "redirect_uri": os.environ[f"{prefix}OIDC_REDIRECT_URI"],
        "post_logout_redirect_uri": os.environ[f"{prefix}OIDC_POST_LOGOUT_REDIRECT_URI"],
        "scopes": os.getenv(f"{prefix}OIDC_SCOPES", "openid profile email"),
        # Preserve the existing default behavior unless a provider-specific prompt override is configured.
        "prompt": os.getenv(f"{prefix}OIDC_PROMPT", "login"),
        "state_secret": os.environ[f"{prefix}OIDC_STATE_SECRET"],
    }


def get_provider_display_name(provider_name: str) -> str:
    """Map provider id to user-facing label shown on login buttons."""
    if provider_name.lower() == "keycloak":
        return "Keycloak"
    if provider_name.lower() == "entra":
        return "Entra ID"
    if provider_name.lower() == "okta":
        return "Okta"
    if provider_name.lower() == "google":
        return "Google"
    return provider_name.capitalize()


def get_provider_icon_svg(provider_name: str) -> str | None:
    """Return inline SVG icon markup for known providers."""
    name = str(provider_name or "").strip().lower()
    icon_file = _ICON_FILES.get(name)
    if not icon_file:
        return None
    return _read_icon_file(icon_file)


@lru_cache(maxsize=16)
def _read_icon_file(icon_file: str) -> str | None:
    """Load and cache provider icon SVG content from assets directory."""
    icon_path = _ICONS_DIR / icon_file
    try:
        return icon_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        log.warning("OIDC icon file not found path=%s", icon_path)
    except OSError as exc:
        log.warning("Failed to read OIDC icon file path=%s error=%s", icon_path, exc)
    return None


def env_flag(name: str, default: bool = False) -> bool:
    """Parse common boolean env var forms (`1/true/yes/on`)."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def auto_provision_enabled() -> bool:
    return env_flag("OIDC_AUTO_PROVISION", False)


def auto_provision_require_email() -> bool:
    return env_flag("OIDC_AUTO_PROVISION_REQUIRE_EMAIL", True)


def allowed_email_domains() -> set[str]:
    """Read optional auto-provision email-domain allowlist from env."""
    raw = os.getenv("OIDC_AUTO_PROVISION_ALLOWED_EMAIL_DOMAINS", "").strip()
    if not raw:
        return set()
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def is_email_allowed(email: str) -> bool:
    allowed = allowed_email_domains()
    if not allowed:
        return True
    if "@" not in email:
        return False
    domain = email.rsplit("@", 1)[1].strip().lower()
    return domain in allowed


def log_oidc_config(cfg: dict[str, str]) -> None:
    """Log selected config fields without exposing secrets."""
    log.info(
        "OIDC config issuer=%s client_id=%s redirect_uri=%s post_logout_redirect_uri=%s scopes=%s prompt=%s "
        "client_secret_present=%s state_secret_present=%s",
        cfg["issuer"],
        cfg["client_id"],
        cfg["redirect_uri"],
        cfg["post_logout_redirect_uri"],
        cfg["scopes"],
        cfg.get("prompt", "login"),
        bool(cfg.get("client_secret")),
        bool(cfg.get("state_secret")),
    )
