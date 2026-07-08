"""OIDC environment variable configuration and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass

from lib.service.env_source import getEnv


@dataclass(frozen=True)
class OIDCProviderConfig:
    """Configuration for a single OIDC provider slot."""

    slot: int
    enabled: bool
    name: str
    icon: str
    issuer: str
    client_id: str
    client_secret: str
    redirect_uri: str
    post_logout_redirect_uri: str
    scopes: str
    prompt: str
    state_secret: str


def env_flag(name: str, default: bool = False) -> bool:
    """Parse common boolean env var forms (`1/true/yes/on`)."""
    raw = getEnv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def is_slot_enabled(slot: int) -> bool:
    """Check if OIDC provider slot is enabled."""
    return env_flag(f"OIDC_{slot}_ENABLED", default=False)


def get_enabled_slots() -> list[int]:
    """Return list of enabled OIDC provider slots (1 and/or 2)."""
    return [slot for slot in (1, 2) if is_slot_enabled(slot)]


def get_provider_name(slot: int) -> str:
    """Get display name for OIDC provider slot."""
    configured_name = getEnv(f"OIDC_{slot}_NAME", "").strip()
    return configured_name or f"OIDC {slot}"


def get_provider_icon(slot: int) -> str:
    """Get icon filename for OIDC provider slot."""
    return getEnv(f"OIDC_{slot}_ICON", "").strip()


def get_provider_issuer(slot: int) -> str:
    """Get issuer URL for OIDC provider slot (trailing slash normalized)."""
    return getEnv(f"OIDC_{slot}_ISSUER", "").rstrip("/")


def get_provider_client_id(slot: int) -> str:
    """Get client ID for OIDC provider slot."""
    return getEnv(f"OIDC_{slot}_CLIENT_ID", "")


def get_provider_client_secret(slot: int) -> str:
    """Get client secret for OIDC provider slot."""
    return getEnv(f"OIDC_{slot}_CLIENT_SECRET", "")


def get_provider_redirect_uri(slot: int) -> str:
    """Get redirect URI for OIDC provider slot."""
    return getEnv(f"OIDC_{slot}_REDIRECT_URI", "")


def get_provider_post_logout_redirect_uri(slot: int) -> str:
    """Get post-logout redirect URI for OIDC provider slot."""
    return getEnv(f"OIDC_{slot}_POST_LOGOUT_REDIRECT_URI", "")


def get_provider_scopes(slot: int) -> str:
    """Get scopes for OIDC provider slot."""
    return getEnv(f"OIDC_{slot}_SCOPES", "openid profile email")


def get_provider_prompt(slot: int) -> str:
    """Get prompt parameter for OIDC provider slot."""
    return getEnv(f"OIDC_{slot}_PROMPT", "login")


def get_provider_state_secret(slot: int) -> str:
    """Get state signing secret for OIDC provider slot."""
    return getEnv(f"OIDC_{slot}_STATE_SECRET", "")


def get_provider_config(slot: int) -> OIDCProviderConfig:
    """Load full configuration for an OIDC provider slot."""
    return OIDCProviderConfig(
        slot=slot,
        enabled=is_slot_enabled(slot),
        name=get_provider_name(slot),
        icon=get_provider_icon(slot),
        issuer=get_provider_issuer(slot),
        client_id=get_provider_client_id(slot),
        client_secret=get_provider_client_secret(slot),
        redirect_uri=get_provider_redirect_uri(slot),
        post_logout_redirect_uri=get_provider_post_logout_redirect_uri(slot),
        scopes=get_provider_scopes(slot),
        prompt=get_provider_prompt(slot),
        state_secret=get_provider_state_secret(slot),
    )


def get_oidc_config_dict(slot: int) -> dict[str, str]:
    """Load OIDC config as dict.

    Raises KeyError if required fields are missing.
    """
    cfg = get_provider_config(slot)

    if not cfg.issuer:
        raise KeyError(f"OIDC_{slot}_ISSUER")
    if not cfg.client_id:
        raise KeyError(f"OIDC_{slot}_CLIENT_ID")
    if not cfg.client_secret:
        raise KeyError(f"OIDC_{slot}_CLIENT_SECRET")
    if not cfg.redirect_uri:
        raise KeyError(f"OIDC_{slot}_REDIRECT_URI")
    if not cfg.post_logout_redirect_uri:
        raise KeyError(f"OIDC_{slot}_POST_LOGOUT_REDIRECT_URI")
    if not cfg.state_secret:
        raise KeyError(f"OIDC_{slot}_STATE_SECRET")

    return {
        "issuer": cfg.issuer,
        "client_id": cfg.client_id,
        "client_secret": cfg.client_secret,
        "redirect_uri": cfg.redirect_uri,
        "post_logout_redirect_uri": cfg.post_logout_redirect_uri,
        "scopes": cfg.scopes,
        "prompt": cfg.prompt,
        "state_secret": cfg.state_secret,
    }


def auto_provision_enabled() -> bool:
    """Check if OIDC auto-provisioning is enabled."""
    return env_flag("OIDC_AUTO_PROVISION", False)


def auto_provision_require_email() -> bool:
    """Check if email claim is required for auto-provisioning."""
    return env_flag("OIDC_AUTO_PROVISION_REQUIRE_EMAIL", True)


def auto_provision_default_role() -> str:
    """Get default role for auto-provisioned users."""
    return getEnv("OIDC_AUTO_PROVISION_DEFAULT_ROLE", "viewer").strip() or "viewer"


def allowed_email_domains() -> set[str]:
    """Read optional auto-provision email-domain allowlist."""
    raw = getEnv("OIDC_AUTO_PROVISION_ALLOWED_EMAIL_DOMAINS", "").strip()
    if not raw:
        return set()
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def is_email_allowed(email: str) -> bool:
    """Check if email domain is in allowlist (empty allowlist permits all)."""
    allowed = allowed_email_domains()
    if not allowed:
        return True
    if "@" not in email:
        return False
    domain = email.rsplit("@", 1)[1].strip().lower()
    return domain in allowed


def group_claim_name() -> str:
    """Get configured claim path containing IdP groups/roles."""
    raw = getEnv("OIDC_GROUP_CLAIM")
    if raw is None:
        raw = getEnv("IDC_GROUP_CLAIM", "groups")
    claim_name = str(raw or "groups").strip()
    return claim_name or "groups"


def group_mapping() -> dict[str, str]:
    """Parse OIDC_GROUP_MAPPING JSON object (idp_group -> local_group_ref)."""
    raw = getEnv("OIDC_GROUP_MAPPING", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    mapping: dict[str, str] = {}
    for key, value in parsed.items():
        source = str(key).strip()
        target = str(value).strip()
        if source and target:
            mapping[source] = target
    return mapping
