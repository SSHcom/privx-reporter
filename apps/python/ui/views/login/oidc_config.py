"""Static OIDC provider/config helpers used by login rendering and callback flow."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from streamlit.logger import get_logger

from lib import env_oidc

log = get_logger(__name__)
_ICONS_DIR = Path(__file__).resolve().parents[2] / "assets" / "icons" / "oidc"


def _slot_index(provider_name: str) -> int | None:
    provider = str(provider_name or "").strip()
    if provider in {"1", "2"}:
        return int(provider)
    return None


def get_oidc_config(provider_name: str) -> dict[str, str]:
    """Load required OIDC environment configuration."""
    provider = str(provider_name or "").strip()
    if not provider or provider.lower() == "oidc":
        raise ValueError("Deprecated OIDC provider id 'oidc'. Use provider slots 1 and/or 2.")

    slot = _slot_index(provider)
    if slot is None:
        raise ValueError("Unsupported OIDC provider slot. Use provider slots 1 or 2.")

    return env_oidc.get_oidc_config_dict(slot)


def get_provider_display_name(provider_name: str) -> str:
    """Map provider id to user-facing label shown on login buttons."""
    slot = _slot_index(provider_name)
    if slot is not None:
        return env_oidc.get_provider_name(slot)
    return "OIDC"


def get_provider_icon_svg(provider_name: str) -> str | None:
    """Return inline SVG icon markup if configured for the provider slot."""
    slot = _slot_index(provider_name)
    if slot is None:
        return None
    icon_file = env_oidc.get_provider_icon(slot)
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
